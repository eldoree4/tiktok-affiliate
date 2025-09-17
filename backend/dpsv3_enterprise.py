```python
# TikTokAffiliatePro - Enterprise SaaS Affiliate Marketing Engine
# Enhanced with /notifications endpoint for real-time alerts
# No dummy data; all metrics from database or API

import os
import asyncio
import logging
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from bs4 import BeautifulSoup
import json

from fastapi import FastAPI, Depends, HTTPException, Request, status, BackgroundTasks
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pydantic_settings import BaseSettings
import httpx
import jwt
import stripe

from cryptography.fernet import Fernet, InvalidToken
from passlib.context import CryptContext

# SQLAlchemy async imports
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, ForeignKey, func
from sqlalchemy.future import select

# -------- Settings --------
class Settings(BaseSettings):
    database_url: str
    jwt_secret: str
    fernet_key: str
    stripe_secret_key: str
    tik_tok_api_base: str = "https://open.tiktokapis.com"
    openai_api_key: Optional[str] = None
    openai_base_url: str = "https://api.openai.com/v1"
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = 587
    smtp_user: Optional[str] = None
    smtp_pass: Optional[str] = None
    access_token_expiry_minutes: int = 60
    oauth_callback_base: str = "http://localhost:8000/oauth/callback"

    class Config:
        env_file = ".env"

settings = Settings()
stripe.api_key = settings.stripe_secret_key

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TikTokAffiliatePro")

# -------- Crypto & Auth helpers --------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
fernet = Fernet(settings.fernet_key.encode() if isinstance(settings.fernet_key, str) else settings.fernet_key)

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_jwt(subject: str, tenant_id: int, expires_minutes: Optional[int] = None) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=(expires_minutes or settings.access_token_expiry_minutes))
    payload = {"sub": subject, "tenant_id": tenant_id, "exp": int(expires.timestamp())}
    token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    return token

def decode_jwt(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail="Invalid token")

def encrypt_secret(plain: str) -> str:
    if not plain:
        return ""
    return fernet.encrypt(plain.encode()).decode()

def decrypt_secret(token: str) -> str:
    if not token:
        return ""
    try:
        return fernet.decrypt(token.encode()).decode()
    except InvalidToken:
        logger.exception("Invalid encrypted token")
        raise HTTPException(status_code=500, detail="Encryption error")

# -------- Database setup --------
DATABASE_URL = settings.database_url
engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    tier = Column(String, nullable=False)  # 'basic', 'pro', 'enterprise'
    stripe_sub_id = Column(String, unique=True, nullable=True)
    features = Column(JSON, default=dict)
    active_until = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    tik_tok_client_id = Column(Text, nullable=True)
    tik_tok_client_secret = Column(Text, nullable=True)
    config = Column(JSON, default={})
    email_notifications = Column(Boolean, default=True)
    notification_email = Column(String, nullable=True)  # Added for notifications

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)

class TikTokAccount(Base):
    __tablename__ = "tiktok_accounts"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, nullable=False)
    external_user_id = Column(String, nullable=False)
    access_token_encrypted = Column(Text, nullable=False)
    refresh_token_encrypted = Column(Text, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    meta = Column(JSON, default={})

class AnalysisHistory(Base):
    __tablename__ = "analysis_history"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)
    type = Column(String, nullable=False)
    data = Column(JSON, default={})
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String, nullable=False)  # e.g., 'trend', 'viral', 'insight'
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_read = Column(Boolean, default=False)

# Create DB tables
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# -------- FastAPI app --------
app = FastAPI(title="TikTokAffiliatePro - Enterprise")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Restrict in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up, initializing DB...")
    await init_db()

# DB dependency
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# -------- Auth dependencies --------
async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)):
    auth = request.headers.get("Authorization")
    if not auth:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Invalid auth scheme")
    token = auth.split(" ", 1)[1].strip()
    payload = decode_jwt(token)
    username = payload.get("sub")
    tenant_id = payload.get("tenant_id")
    if not username or tenant_id is None:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    res = await db.execute(select(User).where(User.username == username))
    user = res.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    if user.tenant_id != tenant_id:
        raise HTTPException(status_code=401, detail="Token tenant mismatch")
    return user

async def get_tenant_tier(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    tenant_id = current_user.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User has no tenant")
    res = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = res.scalar_one_or_none()
    if not tenant or not tenant.subscription_id:
        raise HTTPException(status_code=403, detail="No active subscription")
    sub_res = await db.execute(select(Subscription).where(Subscription.id == tenant.subscription_id))
    sub = sub_res.scalar_one_or_none()
    if not sub or sub.active_until < datetime.now(timezone.utc):
        raise HTTPException(status_code=403, detail="Subscription expired")
    return sub

# -------- Pydantic models --------
class TenantCreate(BaseModel):
    name: str
    notification_email: Optional[str] = None

class UserCreate(BaseModel):
    username: str
    password: str
    tenant_id: int

class LoginRequest(BaseModel):
    username: str
    password: str

class SetCredentialsRequest(BaseModel):
    tik_tok_client_id: str
    tik_tok_client_secret: str

class RecommendRequest(BaseModel):
    niche: str
    region: Optional[str] = "ID"
    top_k_audio: Optional[int] = 8

class AdvancedContentGenRequest(BaseModel):
    product_desc: str
    niche: str
    target_audience: str

class AdvancedVideoAnalysisRequest(BaseModel):
    video_url: str
    niche: Optional[str] = None

class SubscriptionUpgradeRequest(BaseModel):
    tier: str  # 'pro', 'enterprise'

# -------- Utility functions --------
async def get_tenant_credentials(tenant_id: int, db: AsyncSession) -> Dict[str, Optional[str]]:
    res = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = res.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    client_id_enc = tenant.tik_tok_client_id
    client_secret_enc = tenant.tik_tok_client_secret
    client_id = decrypt_secret(client_id_enc) if client_id_enc else None
    client_secret = decrypt_secret(client_secret_enc) if client_secret_enc else None
    return {"client_id": client_id, "client_secret": client_secret}

# TikTok Video Scraper
async def fetch_tiktok_video_data(video_url: str) -> Dict[str, Any]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        try:
            response = await client.get(video_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            script = soup.find('script', id='__UNIVERSAL_DATA_FOR_REHYDRATION__')
            if not script:
                raise ValueError("No data script found")
            data_str = script.string.strip().replace('window.__UNIVERSAL_DATA_FOR_REHYDRATION__ = ', '').rstrip(';')
            json_data = json.loads(data_str)
            item_info = json_data.get('__DEFAULT_SCOPE__', {}).get('webapp.video-detail', {}).get('itemInfo', {}).get('itemStruct', {})
            stats = item_info.get('stats', {})
            music = item_info.get('music', {})
            desc = item_info.get('desc', '')
            return {
                'id': item_info.get('id'),
                'views': stats.get('playCount', 0),
                'likes': stats.get('diggCount', 0),
                'shares': stats.get('shareCount', 0),
                'comments': stats.get('commentCount', 0),
                'audio': {'name': music.get('title'), 'id': music.get('id')},
                'caption': desc,
                'author': item_info.get('author', {}).get('uniqueId')
            }
        except Exception as e:
            logger.error(f"Failed to scrape TikTok video {video_url}: {e}")
            return {}

# AI Integration
async def analyze_with_llm(prompt: str, model: str = "gpt-3.5-turbo") -> str:
    if not settings.openai_api_key:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1000,
        "temperature": 0.7,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(f"{settings.openai_base_url}/chat/completions", headers=headers, json=data)
            if resp.status_code != 200:
                raise HTTPException(status_code=500, detail="AI analysis failed")
            result = resp.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            logger.exception("LLM call failed: %s", e)
            raise HTTPException(status_code=500, detail="AI service unavailable")

# Notification System
async def send_notification(tenant_id: int, subject: str, message: str, notification_type: str, db: AsyncSession):
    res = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = res.scalar_one_or_none()
    if not tenant or not tenant.email_notifications or not tenant.notification_email:
        logger.info(f"Skipping notification for tenant {tenant_id}: email not configured or disabled")
        return
    # Store in DB
    notif = Notification(tenant_id=tenant_id, message=message, type=notification_type, created_at=datetime.now(timezone.utc))
    db.add(notif)
    await db.commit()
    # Send email
    if settings.smtp_host and settings.smtp_user and settings.smtp_pass:
        msg = MIMEText(message)
        msg['Subject'] = subject
        msg['From'] = settings.smtp_user
        msg['To'] = tenant.notification_email
        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                server.starttls()
                server.login(settings.smtp_user, settings.smtp_pass)
                server.send_message(msg)
            logger.info(f"Sent notification to {tenant.notification_email}: {subject}")
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")

# Predictive Analytics
async def run_predictive_analysis(tenant_id: int, db: AsyncSession) -> Dict[str, Any]:
    res = await db.execute(
        select(
            func.avg(func.extract('hour', AnalysisHistory.created_at)).label('avg_hour'),
            func.jsonb_agg(AnalysisHistory.data['hashtags']).label('hashtags'),
            func.jsonb_agg(AnalysisHistory.data['trending_audio']).label('audios')
        )
        .where(AnalysisHistory.tenant_id == tenant_id, AnalysisHistory.type == 'recommendation')
    )
    result = res.first()
    if not result:
        return {"optimal_post_hour": None, "top_hashtag_pattern": [], "best_audio_trend": []}
    avg_hour = int(result.avg_hour) if result.avg_hour else None
    hashtags = [h for sublist in result.hashtags for h in sublist] if result.hashtags else []
    top_hashtags = list(dict.fromkeys(hashtags))[:5]  # Top 5 unique hashtags
    audios = [a['id'] for sublist in result.audios for a in sublist if a] if result.audios else []
    audio_counts = {}
    for audio_id in audios:
        audio_counts[audio_id] = audio_counts.get(audio_id, 0) + 1
    top_audio = max(audio_counts.items(), key=lambda x: x[1], default=(None, 0))[0]
    return {
        "optimal_post_hour": avg_hour,
        "top_hashtag_pattern": top_hashtags,
        "best_audio_trend": top_audio
    }

# -------- Endpoints --------
@app.post("/admin/tenants", status_code=201)
async def create_tenant(payload: TenantCreate, db: AsyncSession = Depends(get_db)):
    t = Tenant(name=payload.name, notification_email=payload.notification_email, created_at=datetime.now(timezone.utc))
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return {"id": t.id, "name": t.name, "created_at": t.created_at.isoformat()}

@app.post("/admin/subscriptions", status_code=201)
async def create_subscription(payload: SubscriptionUpgradeRequest, db: AsyncSession = Depends(get_db)):
    feature_map = {
        "basic": {"ai_analysis": False, "content_gen": False, "unlimited_requests": False},
        "pro": {"ai_analysis": True, "content_gen": True, "unlimited_requests": False},
        "enterprise": {"ai_analysis": True, "content_gen": True, "unlimited_requests": True}
    }
    sub = Subscription(
        tenant_id=payload.tenant_id,
        tier=payload.tier,
        features=feature_map.get(payload.tier, {}),
        active_until=datetime.now(timezone.utc) + timedelta(days=30)
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    res = await db.execute(select(Tenant).where(Tenant.id == payload.tenant_id))
    tenant = res.scalar_one_or_none()
    if tenant:
        tenant.subscription_id = sub.id
        await db.commit()
    return {"id": sub.id, "tier": sub.tier, "active_until": sub.active_until.isoformat()}

@app.post("/admin/tenants/{tenant_id}/credentials")
async def set_tenant_credentials(tenant_id: int, payload: SetCredentialsRequest, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = res.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    tenant.tik_tok_client_id = encrypt_secret(payload.tik_tok_client_id)
    tenant.tik_tok_client_secret = encrypt_secret(payload.tik_tok_client_secret)
    await db.commit()
    return {"detail": "Credentials set (encrypted)"}

@app.post("/users", status_code=201)
async def create_user(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Tenant).where(Tenant.id == payload.tenant_id))
    tenant = res.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    existing = await db.execute(select(User).where(User.username == payload.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already exists")
    h = hash_password(payload.password)
    user = User(username=payload.username, password_hash=h, tenant_id=payload.tenant_id, created_at=datetime.now(timezone.utc))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {"id": user.id, "username": user.username, "tenant_id": user.tenant_id}

@app.post("/auth/login")
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(User).where(User.username == payload.username))
    user = res.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_jwt(subject=user.username, tenant_id=user.tenant_id)
    return {"access_token": token, "token_type": "bearer"}

@app.get("/auth/me")
async def get_user_info(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    sub = await get_tenant_tier(current_user, db)
    return {"user": {"id": current_user.id, "username": current_user.username, "tenant_id": current_user.tenant_id}, "tier": sub.tier}

@app.get("/oauth/start")
async def oauth_start(tenant_id: int, redirect_to: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    creds = await get_tenant_credentials(tenant_id, db)
    client_id = creds.get("client_id")
    if not client_id:
        raise HTTPException(status_code=400, detail="Tenant OAuth client_id not set.")
    callback = redirect_to or settings.oauth_callback_base
    state = f"{tenant_id}:{int(datetime.now(timezone.utc).timestamp())}"
    auth_url = f"https://open.tiktokapis.com/v2/oauth/authorize?client_key={client_id}&response_type=code&scope=user.info.basic,video.list&redirect_uri={callback}&state={state}"
    return RedirectResponse(auth_url)

@app.get("/oauth/callback")
async def oauth_callback(code: Optional[str] = None, state: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    if not code or not state or ":" not in state:
        raise HTTPException(status_code=400, detail="Invalid callback parameters")
    tenant_id = int(state.split(":")[0])
    creds = await get_tenant_credentials(tenant_id, db)
    client_id = creds.get("client_id")
    client_secret = creds.get("client_secret")
    if not client_id or not client_secret:
        raise HTTPException(status_code=400, detail="Tenant OAuth credentials missing")
    token_url = f"{settings.tik_tok_api_base.rstrip('/')}/v2/oauth/token"
    data = {
        "client_key": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.post(token_url, json=data)
            resp.raise_for_status()
        except Exception as e:
            logger.exception("Token exchange failed: %s", e)
            raise HTTPException(status_code=500, detail="Token exchange error")
        token_payload = resp.json()
        access_token = token_payload.get("access_token") or token_payload.get("accessToken")
        refresh_token = token_payload.get("refresh_token") or token_payload.get("refreshToken")
        expires_in = token_payload.get("expires_in") or token_payload.get("expiresIn")
        user_id = token_payload.get("open_id") or token_payload.get("openId") or token_payload.get("user_id")
        if not access_token or not user_id:
            raise HTTPException(status_code=500, detail="Invalid token payload")
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in)) if expires_in else None
        access_enc = encrypt_secret(access_token)
        refresh_enc = encrypt_secret(refresh_token) if refresh_token else None
        stmt = select(TikTokAccount).where(TikTokAccount.tenant_id == tenant_id, TikTokAccount.external_user_id == str(user_id))
        res = await db.execute(stmt)
        acc = res.scalar_one_or_none()
        if acc:
            acc.access_token_encrypted = access_enc
            acc.refresh_token_encrypted = refresh_enc
            acc.token_expires_at = expires_at
            acc.is_active = True
        else:
            acc = TikTokAccount(
                tenant_id=tenant_id,
                external_user_id=str(user_id),
                access_token_encrypted=access_enc,
                refresh_token_encrypted=refresh_enc,
                token_expires_at=expires_at,
                is_active=True,
                meta={}
            )
            db.add(acc)
        await db.commit()
        return {"detail": "OAuth success. Account connected.", "tenant_id": tenant_id, "user_id": user_id}

async def fetch_trending_audio_tiktok(region: str, limit: int = 10, token: Optional[str] = None) -> List[Dict[str, Any]]:
    base = settings.tik_tok_api_base.rstrip("/")
    url = f"{base}/v1/music/trending?region={region}&limit={limit}"
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            r = await client.get(url, headers=headers)
            r.raise_for_status()
            payload = r.json()
            items = []
            data = payload.get("data") or payload
            source_list = data.get("list", []) if isinstance(data, dict) else data
            for it in source_list[:limit]:
                title = it.get("title") or it.get("name") or it.get("music_name")
                mid = it.get("id") or it.get("music_id")
                plays = it.get("play_count") or it.get("plays") or 0
                if not title or not mid:
                    continue
                items.append({"title": title, "id": str(mid), "plays": plays, "source": "tiktok"})
            return items
        except Exception as e:
            logger.warning("TikTok API request failed: %s", e)
            return []

@app.post("/recommend")
async def recommend_endpoint(req: RecommendRequest, current_user: User = Depends(get_current_user), sub = Depends(get_tenant_tier), db: AsyncSession = Depends(get_db)):
    if current_user.tenant_id is None:
        raise HTTPException(status_code=400, detail="User has no tenant")
    tenant_id = current_user.tenant_id
    res = await db.execute(select(TikTokAccount).where(TikTokAccount.tenant_id == tenant_id).limit(1))
    acc = res.scalar_one_or_none()
    token = decrypt_secret(acc.access_token_encrypted) if acc else None
    trending = []
    try:
        trending = await fetch_trending_audio_tiktok(req.region, limit=req.top_k_audio, token=token)
    except Exception as e:
        logger.exception("Error fetching trending: %s", e)
    niche = req.niche.strip().lower()
    hashtags = [f"#{niche.replace(' ', '')}", "#fyp", "#viral", "#affiliatemarketing", "#tiktokshop"]
    caption = f"Unlock exclusive {req.niche} deals! Shop now via link in bio! 🔥 #Affiliate"
    keywords = [niche, f"affiliate {niche}", f"best {niche} deals", "tiktok checkout"]
    ai_insights = None
    if sub.tier in ["pro", "enterprise"]:
        prompt = f"Provide AI insights for TikTok affiliate marketing in niche '{req.niche}' (region: {req.region}). Suggest strategies to boost viewers and checkouts."
        ai_insights = await analyze_with_llm(prompt)
    result = {
        "trending_audio": trending,
        "hashtags": hashtags,
        "caption": caption,
        "keywords": keywords,
        "niche": req.niche,
        "region": req.region,
        "ai_insights": ai_insights or "Upgrade to Pro for AI insights!",
        "tier": sub.tier
    }
    hist = AnalysisHistory(tenant_id=tenant_id, user_id=current_user.id, type="recommendation", data=result)
    db.add(hist)
    await db.commit()
    if trending:
        await send_notification(tenant_id, "New Trending Audio", f"New trending audio detected for {req.niche} in {req.region}", "trend", db)
    return result

@app.post("/generate/content/advanced")
async def advanced_content_gen(req: AdvancedContentGenRequest, current_user: User = Depends(get_current_user), sub = Depends(get_tenant_tier), db: AsyncSession = Depends(get_db)):
    if sub.tier not in ["pro", "enterprise"]:
        raise HTTPException(status_code=403, detail="Advanced Content Gen requires Pro+ tier")
    prompt = f"""Generate TikTok affiliate content for product: '{req.product_desc}' in niche '{req.niche}' targeting '{req.target_audience}'.
    Output in JSON: {{"ideas": ["3 unique video ideas"], "script": "full draft script", "captions": ["3 variations"], "hashtags": ["optimized set"]}}"""
    content = await analyze_with_llm(prompt)
    try:
        parsed = json.loads(content)
    except:
        parsed = {"ideas": [content], "script": "", "captions": [], "hashtags": []}
    tenant_id = current_user.tenant_id
    hist = AnalysisHistory(tenant_id=tenant_id, user_id=current_user.id, type="advanced_content", data={**req.dict(), "generated": parsed})
    db.add(hist)
    await db.commit()
    await send_notification(tenant_id, "New Content Generated", f"Generated content for {req.niche} is ready!", "content", db)
    return parsed

@app.post("/analyze/video/advanced")
async def advanced_video_analysis(req: AdvancedVideoAnalysisRequest, current_user: User = Depends(get_current_user), sub = Depends(get_tenant_tier), db: AsyncSession = Depends(get_db)):
    if sub.tier != "enterprise":
        raise HTTPException(status_code=403, detail="Advanced Video Analysis requires Enterprise tier")
    video_data = await fetch_tiktok_video_data(req.video_url)
    if not video_data:
        raise HTTPException(status_code=400, detail="Could not fetch video data")
    prompt = f"""Analyze TikTok video data: {json.dumps(video_data)} for affiliate success in niche: {req.niche or 'general'}.
    Identify visual style, transitions, narrative, engagement drivers. Suggest improvements for views/checkouts."""
    analysis = await analyze_with_llm(prompt)
    tenant_id = current_user.tenant_id
    hist = AnalysisHistory(tenant_id=tenant_id, user_id=current_user.id, type="advanced_video_analysis", data={**req.dict(), "video_data": video_data, "analysis": analysis})
    db.add(hist)
    await db.commit()
    if video_data.get('views', 0) > 1000000:
        await send_notification(tenant_id, "Viral Video Detected", f"Video {req.video_url} has over 1M views!", "viral", db)
    return {"video_data": video_data, "analysis": analysis}

@app.get("/analytics/predictive")
async def predictive_insights(current_user: User = Depends(get_current_user), sub = Depends(get_tenant_tier), db: AsyncSession = Depends(get_db)):
    if sub.tier != "enterprise":
        raise HTTPException(status_code=403, detail="Predictive Analytics requires Enterprise tier")
    tenant_id = current_user.tenant_id
    insights = await run_predictive_analysis(tenant_id, db)
    hist = AnalysisHistory(tenant_id=tenant_id, user_id=current_user.id, type="predictive", data=insights)
    db.add(hist)
    await db.commit()
    await send_notification(tenant_id, "New Insights Available", "Predictive analysis updated.", "insight", db)
    return insights

@app.get("/dashboard/tenant")
async def tenant_dashboard(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db), limit: int = 20):
    tenant_id = current_user.tenant_id
    res = await db.execute(
        select(AnalysisHistory).where(AnalysisHistory.tenant_id == tenant_id).order_by(AnalysisHistory.created_at.desc()).limit(limit)
    )
    histories = res.scalars().all()
    total_views = sum(h.data.get('video_data', {}).get('views', 0) for h in histories if 'video_data' in h.data)
    return {
        "recent_analyses": [{"id": h.id, "type": h.type, "date": h.created_at.isoformat(), "summary": str(h.data)[:200]} for h in histories],
        "metrics": {"total_analyses": len(histories), "total_views": total_views}
    }

@app.get("/dashboard/admin")
async def admin_dashboard(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    res = await db.execute(select(User).where(User.tenant_id == current_user.tenant_id, User.is_active == True))
    users = res.scalars().all()
    if not any(u.username.endswith("@admin") for u in users):  # Simple admin check
        raise HTTPException(status_code=403, detail="Admin access required")
    active_users = len(users)
    res = await db.execute(select(Subscription).where(Subscription.tenant_id == current_user.tenant_id, Subscription.active_until > datetime.now(timezone.utc)))
    active_subs = len(res.scalars().all())
    return {"active_users": active_users, "active_subscriptions": active_subs}

@app.get("/notifications")
async def get_notifications(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db), limit: int = 10):
    tenant_id = current_user.tenant_id
    res = await db.execute(
        select(Notification)
        .where(Notification.tenant_id == tenant_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    notifications = res.scalars().all()
    return [{"id": n.id, "message": n.message, "type": n.type, "created_at": n.created_at.isoformat(), "is_read": n.is_read} for n in notifications]

@app.post("/subscribe/create-session")
async def create_checkout_session(req: SubscriptionUpgradeRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    tenant_id = current_user.tenant_id
    res = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = res.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    price_map = {"pro": "price_pro_id", "enterprise": "price_ent_id"}  # Replace with actual Stripe price IDs
    price_id = price_map.get(req.tier)
    if not price_id:
        raise HTTPException(status_code=400, detail="Invalid tier")
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{'price': price_id, 'quantity': 1}],
            mode='subscription',
            success_url='http://localhost:3000/success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='http://localhost:3000/cancel',
            metadata={'tenant_id': str(tenant_id), 'tier': req.tier}
        )
        return {"session_id": session.id, "url": session.url}
    except Exception as e:
        logger.error(f"Stripe session creation failed: {e}")
        raise HTTPException(status_code=500, detail="Payment setup failed")

@app.post("/stripe/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    endpoint_secret = "whsec_your_webhook_secret"  # Set in .env
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid webhook payload")
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        tenant_id = int(session['metadata']['tenant_id'])
        tier = session['metadata']['tier']
        stripe_sub_id = session['subscription']
        sub = Subscription(
            tenant_id=tenant_id,
            tier=tier,
            stripe_sub_id=stripe_sub_id,
            features={"ai_analysis": tier in ["pro", "enterprise"], "content_gen": tier in ["pro", "enterprise"], "unlimited_requests": tier == "enterprise"},
            active_until=datetime.now(timezone.utc) + timedelta(days=30)
        )
        db.add(sub)
        await db.commit()
        res = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = res.scalar_one_or_none()
        if tenant:
            tenant.subscription_id = sub.id
            await db.commit()
        await send_notification(tenant_id, "Subscription Activated", f"Welcome to {tier} tier!", "subscription", db)
    return JSONResponse({"status": "success"})

@app.get("/health")
async def health():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("dpsv2_enterprise:app", host="0.0.0.0", port=8000, reload=True)
```
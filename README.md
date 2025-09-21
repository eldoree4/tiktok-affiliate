# TikTok Kit v2.2 - Advanced CLI for TikTok API Integration

TikTok Kit v2.2 is a powerful command-line tool designed for businesses, marketers, and developers to interact with TikTok's APIs (Business, Research, and Shop). It offers features like OAuth authentication, trend-based content generation, video analysis, ad promotion, affiliate link creation, and advanced FYP/keyword analysis with machine learning and visualizations.

## Features
- **OAuth Login with PKCE**: Automated login with a local callback server.
- **Content Generation**: Create trend-based content ideas, scripts, and captions.
- **Video Analysis**: Analyze video performance using TikTok's Research API.
- **Ad Promotion**: Launch real TikTok ad campaigns with customizable targets.
- **FYP/Keyword Analysis**: Analyze trending hashtags and peak posting hours with ML clustering and visualizations.
- **Affiliate Booster**: Generate affiliate links and track commissions via TikTok Shop API.
- **Enterprise Dashboard**: Visualize analytics and export data to CSV.
- **Secure Data Storage**: Encrypts user tokens and credentials with Fernet encryption.
- **Robust Error Handling**: Retries failed API calls and validates user inputs.

## Prerequisites
Before using TikTok Kit v2.2, ensure you have the following:
- **Python 3.8+**: Install Python from [python.org](https://www.python.org/downloads/).
- **TikTok API Credentials**:
  - **App ID and Secret**: Obtain from [TikTok Developers Portal](https://developers.tiktok.com).
  - **Advertiser ID**: Get from [TikTok Business Center](https://business.tiktok.com).
  - **Research Access Token**: Optional, for Research API access (apply via TikTok Developers Portal).
  - **Shop App ID and Secret**: For TikTok Shop affiliate features, obtain from [TikTok Shop Partner](https://partner.tiktokshop.com).
- **Internet Connection**: Required for API calls and OAuth authentication.
- **Termux (Optional)**: For running on Android devices.

## Installation

1. **Clone or Download the Repository**:
   ```bash
   git clone <repository-url>
   cd tiktok-kit

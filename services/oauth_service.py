"""
OAuth Service - Google OAuth Implementation with Drive Access
"""
from typing import Optional, Dict
import httpx
from fastapi import HTTPException

class OAuthService:
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.google_auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        self.google_token_url = "https://oauth2.googleapis.com/token"
        self.google_userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        
        # ✅ Define scopes - including Drive access
        self.scopes = [
            "openid",
            "email",
            "profile",
            "https://www.googleapis.com/auth/drive.file"  # Drive file access
        ]
    
    def get_authorization_url(self, state: str = None) -> str:
        """Generate Google OAuth authorization URL with Drive scope"""
        # Join scopes with space
        scope_string = " ".join(self.scopes)
        
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": scope_string,
            "access_type": "offline",  # ✅ Required for refresh token
            "prompt": "consent",  # ✅ Force consent to get refresh token every time
            "include_granted_scopes": "true"  # ✅ Incremental authorization
        }
        
        if state:
            params["state"] = state
        
        # Build query string
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        auth_url = f"{self.google_auth_url}?{query_string}"
        
        print(f"🔗 Authorization URL: {auth_url[:150]}...")
        
        return auth_url

    async def exchange_code_for_token(self, code: str) -> Dict:
        """
        Exchange authorization code for access token and refresh token
        
        Returns:
            {
                "access_token": "ya29.xxx...",
                "refresh_token": "1//xxx...",  # Only on first auth or with prompt=consent
                "expires_in": 3599,
                "scope": "...",
                "token_type": "Bearer"
            }
        """
        data = {
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code"
        }
        
        print(f"🔄 Exchanging code for token...")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.google_token_url, data=data)
                
                if response.status_code != 200:
                    error_detail = response.text
                    print(f"❌ Token exchange failed: {error_detail}")
                    raise HTTPException(400, f"Failed to get access token: {error_detail}")
                
                token_data = response.json()
                
                print(f"✅ Access token received: {token_data.get('access_token', '')[:20]}...")
                print(f"✅ Refresh token: {'Yes' if token_data.get('refresh_token') else 'No'}")
                print(f"✅ Expires in: {token_data.get('expires_in')} seconds")
                
                return token_data
                
        except httpx.RequestError as e:
            print(f"❌ Request error during token exchange: {e}")
            raise HTTPException(500, f"Network error: {str(e)}")
    
    async def refresh_access_token(self, refresh_token: str) -> Dict:
        """
        Refresh expired access token using refresh token
        
        Args:
            refresh_token: The refresh token obtained during initial authorization
            
        Returns:
            {
                "access_token": "ya29.xxx...",
                "expires_in": 3599,
                "scope": "...",
                "token_type": "Bearer"
            }
        """
        data = {
            "refresh_token": refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token"
        }
        
        print(f"🔄 Refreshing access token...")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.google_token_url, data=data)
                
                if response.status_code != 200:
                    error_detail = response.text
                    print(f"❌ Token refresh failed: {error_detail}")
                    raise HTTPException(400, f"Failed to refresh token: {error_detail}")
                
                token_data = response.json()
                
                print(f"✅ New access token: {token_data.get('access_token', '')[:20]}...")
                print(f"✅ Expires in: {token_data.get('expires_in')} seconds")
                
                return token_data
                
        except httpx.RequestError as e:
            print(f"❌ Request error during token refresh: {e}")
            raise HTTPException(500, f"Network error: {str(e)}")
    
    async def get_user_info(self, access_token: str) -> Dict:
        """
        Get user information from Google
        
        Returns:
            {
                "id": "123456789",
                "email": "user@example.com",
                "verified_email": true,
                "name": "John Doe",
                "given_name": "John",
                "family_name": "Doe",
                "picture": "https://...",
                "locale": "en"
            }
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        
        print(f"👤 Fetching user info...")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.google_userinfo_url, headers=headers)
                
                if response.status_code != 200:
                    error_detail = response.text
                    print(f"❌ Failed to get user info: {error_detail}")
                    raise HTTPException(400, f"Failed to get user info: {error_detail}")
                
                user_info = response.json()
                
                print(f"✅ User info received: {user_info.get('email')}")
                
                return user_info
                
        except httpx.RequestError as e:
            print(f"❌ Request error during user info fetch: {e}")
            raise HTTPException(500, f"Network error: {str(e)}")
    
    async def revoke_token(self, token: str) -> bool:
        """
        Revoke an access token or refresh token
        
        Args:
            token: Access token or refresh token to revoke
            
        Returns:
            True if successful, False otherwise
        """
        revoke_url = "https://oauth2.googleapis.com/revoke"
        
        print(f"🔒 Revoking token...")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    revoke_url,
                    data={"token": token},
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                if response.status_code == 200:
                    print(f"✅ Token revoked successfully")
                    return True
                else:
                    print(f"⚠️ Token revocation failed: {response.text}")
                    return False
                    
        except httpx.RequestError as e:
            print(f"❌ Request error during token revocation: {e}")
            return False
    
    def validate_token_format(self, access_token: str) -> bool:
        """
        Validate if token looks like a valid Google access token
        Google access tokens typically start with 'ya29'
        """
        if not access_token:
            return False
        
        # Google access tokens usually start with 'ya29'
        if access_token.startswith('ya29'):
            return True
        
        print(f"⚠️ Token format looks suspicious: {access_token[:10]}...")
        return False
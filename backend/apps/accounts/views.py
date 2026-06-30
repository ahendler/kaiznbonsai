from django.conf import settings
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import LoginSerializer, RegisterSerializer, UserSerializer


def _set_refresh_cookie(response, refresh_token: str) -> None:
    """Write the refresh token into an httpOnly cookie.

    Keeping the refresh token out of JS-accessible storage (localStorage,
    sessionStorage) reduces the blast radius of an XSS vulnerability — an
    attacker can use the access token until it expires (15 min) but cannot
    silently re-authenticate by stealing the refresh token.
    """
    jwt_settings = settings.SIMPLE_JWT
    response.set_cookie(
        key=jwt_settings['AUTH_COOKIE'],
        value=refresh_token,
        httponly=jwt_settings['AUTH_COOKIE_HTTP_ONLY'],
        samesite=jwt_settings['AUTH_COOKIE_SAMESITE'],
        secure=jwt_settings['AUTH_COOKIE_SECURE'],
        max_age=int(jwt_settings['REFRESH_TOKEN_LIFETIME'].total_seconds()),
    )


class RegisterView(generics.CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer


class LoginView(TokenObtainPairView):
    permission_classes = (AllowAny,)
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            # Move the refresh token from the response body into an httpOnly
            # cookie so it is never accessible to JavaScript.
            refresh_token = response.data.pop('refresh', None)
            if refresh_token:
                _set_refresh_cookie(response, refresh_token)
        return response


class RefreshView(TokenRefreshView):
    """Reads the refresh token from the httpOnly cookie.

    Falls back to the request body when the cookie is unavailable (e.g. Safari
    ITP or privacy-hardened browsers). The frontend keeps a sessionStorage
    copy for that fallback path.
    """
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        cookie_name = settings.SIMPLE_JWT['AUTH_COOKIE']
        refresh_token = request.COOKIES.get(cookie_name) or request.data.get('refresh')

        if not refresh_token:
            return Response(
                {'detail': 'Refresh token not found.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # request.data is immutable in DRF; write to the backing store directly
        # so the parent TokenRefreshView can read the token.
        request._full_data = {'refresh': refresh_token}

        response = super().post(request, *args, **kwargs)

        if response.status_code == status.HTTP_200_OK:
            new_refresh = response.data.pop('refresh', None)
            if new_refresh:
                _set_refresh_cookie(response, new_refresh)

        return response


class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        cookie_name = settings.SIMPLE_JWT['AUTH_COOKIE']
        refresh_token = request.COOKIES.get(cookie_name)

        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except TokenError:
                # Token already expired or invalid — treat as a no-op.
                pass

        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie(cookie_name)
        return response


class MeView(generics.RetrieveAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

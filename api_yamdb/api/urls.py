from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CategoryViewSet, CommentViewSet, GenriesViewSet,
    ReviewViewSet, TitlesViewSet, UserViewSet, get_jwt_token, register
)

v1_router = DefaultRouter()
v1_router.register('users', UserViewSet)
v1_router.register('categories', CategoryViewSet)
v1_router.register('genres', GenriesViewSet)
v1_router.register('titles', TitlesViewSet)
v1_router.register(
    r'titles/(?P<title_id>[\d]+)/reviews',
    ReviewViewSet,
    basename='reviews'
)
v1_router.register(
    r'titles/(?P<title_id>[\d]+)/reviews/(?P<review_id>[\d]+)/comments',
    CommentViewSet,
    basename='comments'
)
auth_path = [
    path('signup/', register, name='sign_up'),
    path('token/', get_jwt_token, name='get_token'),
]

urlpatterns = [
    path('v1/auth/', include(auth_path)),
    path('v1/', include(v1_router.urls)),
]

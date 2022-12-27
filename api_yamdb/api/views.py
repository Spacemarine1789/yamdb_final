from datetime import datetime
from django.db.models import Avg
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import (
    filters, permissions, serializers, status, viewsets
)
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework_simplejwt.tokens import AccessToken

from .filters import TitleFilter
from .mixins import CustomViewSet
from .permissions import IsAdmin, IsAdminOrReadOnly, IsStaffOrAuthorOrReadOnly
from reviews.models import Category, Genre, Title, Review, User
from .serializers import (
    CategorySerializer, CommentSerializer, GenreSerializer,
    GetTokenSerializer, ReadOnlyTitleSerializer, ReviewSerializer,
    SignUpSerializer, TitlesSerializer, UserSerializer, UserEditSerializer
)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register(request):
    """
    Получение код подтверждения на переданный email.
    Права доступа: Доступно без токена.
    Использовать имя 'me' в качестве username запрещено.
    Поля email и username должны быть уникальными.
    """
    serializer = SignUpSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    user = get_object_or_404(
        User,
        username=serializer.validated_data['username'],
        email=serializer.validated_data['email'],
    )
    confirmation_code = default_token_generator.make_token(user)
    send_mail(
        subject='Registration',
        message=f'Confirmation code: {confirmation_code}',
        from_email=None,
        recipient_list=[user.email],
    )

    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def get_jwt_token(request):
    """
    Получение JWT-токена в обмен на username и confirmation code.
    Права доступа: Доступно без токена.
    """
    serializer = GetTokenSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = get_object_or_404(
        User,
        username=serializer.validated_data['username']
    )

    if default_token_generator.check_token(
        user, serializer.validated_data['confirmation_code']
    ):
        token = AccessToken.for_user(user)
        return Response({'token': str(token)}, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserViewSet(viewsets.ModelViewSet):
    """
    Получение списка всех пользователей.
    Права доступа: Администратор.
    Возможно получение и редактирование собственного профиля
    зарегестрированым пользователем по адресу 'me'
    """
    lookup_field = 'username'
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (IsAdmin,)

    @action(
        methods=['get'],
        detail=False,
        url_path='me',
        permission_classes=[permissions.IsAuthenticated],
        serializer_class=UserEditSerializer,
    )
    def users_own_profile(self, request):
        user = request.user
        serializer = self.get_serializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @users_own_profile.mapping.patch
    def patch_own_profile(self, request):
        user = request.user
        serializer = self.get_serializer(
            user,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class CategoryViewSet(CustomViewSet):
    """
    Получение списка всех категорий.
    Права доступа: Администратор или только чтение.
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = (IsAdminOrReadOnly,)
    lookup_field = 'slug'
    filter_backends = (filters.SearchFilter,)
    search_fields = ("name",)


class GenriesViewSet(CustomViewSet):
    """
    Получение списка всех жанров.
    Права доступа: Администратор или только чтение.
    """
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    permission_classes = (IsAdminOrReadOnly,)
    lookup_field = 'slug'
    filter_backends = (filters.SearchFilter,)
    search_fields = ("name",)


class TitlesViewSet(viewsets.ModelViewSet):
    """
    Получение списка всех произведений.
    Права доступа: Администратор или только чтение.
    """
    queryset = Title.objects.annotate(
        Avg("reviews__score")
    )
    permission_classes = (IsAdminOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = TitleFilter

    def get_serializer_class(self):
        if self.action in ("retrieve", "list"):
            return ReadOnlyTitleSerializer
        return TitlesSerializer

    def validate(self, data):
        """
        Проверка текущего года.
        """
        if data['year'] > int(datetime.now().year):
            raise serializers.ValidationError("Введенная дата больше текущей")
        return data


class ReviewViewSet(viewsets.ModelViewSet):
    """
    Получение списка всех отзывов к произведению.
    Права доступа: Администратор, модератор, автор или только чтение.
    """
    serializer_class = ReviewSerializer
    permission_classes = (IsStaffOrAuthorOrReadOnly,)

    def get_queryset(self):
        title = get_object_or_404(Title, id=self.kwargs.get('title_id'))
        return title.reviews.all()

    def perform_create(self, serializer):
        title = get_object_or_404(Title, id=self.kwargs.get('title_id'))
        if self.action in ("create",):
            if Review.objects.filter(
                title=title, author=self.request.user
            ).exists():
                raise ValidationError('Вы не можете добавить более'
                                      'одного отзыва на произведение')
        serializer.save(author=self.request.user, title=title)


class CommentViewSet(viewsets.ModelViewSet):
    """
    Получение списка всех коментариев к отзыву.
    Права доступа: Администратор, модератор, автор или только чтение.
    """
    serializer_class = CommentSerializer
    permission_classes = (IsStaffOrAuthorOrReadOnly,)

    def get_queryset(self):
        review = get_object_or_404(
            Review,
            id=self.kwargs.get('review_id'),
            title=self.kwargs.get('title_id')
        )
        return review.сomments.all()

    def perform_create(self, serializer):
        review = get_object_or_404(
            Review,
            id=self.kwargs.get('review_id'),
            title=self.kwargs.get('title_id')
        )
        serializer.save(
            author=self.request.user,
            review=review
        )

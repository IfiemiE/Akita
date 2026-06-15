from rest_framework import serializers
from .models import(
    Language, Dialect, Community, AkitaCommunity, MediaTag, Category, SiteSetting
)


class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = ['id', 'name', 'iso_code', 'is_target']


class DialectSerializer(serializers.ModelSerializer):
    language_name = serializers.CharField(source='language.name', read_only=True)
    class Meta:
        model = Dialect
        fields = ['id', 'name', 'language_name', 'iso_code', 'is_target']


class CommunitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Community
        fields = ['id', 'name', 'alternate_names', 'description']


class AkitaCommunitySerializer(serializers.ModelSerializer):
    class Meta:
        model = AkitaCommunity
        fields = ['id', 'name', 'alternate_names', 'description', 'is_active']
        

class MediaTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaTag
        fields = ['id', 'name', 'slug', 'description']


class CategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'parent', 'description', 'children']

    def get_children(self, obj):
        if obj.children.exists():
            return CategorySerializer(obj.children.all(), many=True).data
        return []


class SiteSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSetting
        fields = ['id', 'key', 'value', 'description']


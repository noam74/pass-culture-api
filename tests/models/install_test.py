from pcapi.models import Feature
from pcapi.models.feature import FEATURES_DISABLED_BY_DEFAULT
from pcapi.models.feature import FeatureToggle
from pcapi.models.install import install_features


class InstallFeaturesTest:
    def test_creates_active_features_in_database(self, app):
        # Given
        Feature.query.delete()

        # When
        install_features()

        # Then
        for feature_toggle in FeatureToggle:
            feature = Feature.query.filter_by(name=feature_toggle.name).one()
            assert feature.description == feature_toggle.value
            if feature_toggle in FEATURES_DISABLED_BY_DEFAULT:
                assert not feature.isActive
            else:
                assert feature.isActive

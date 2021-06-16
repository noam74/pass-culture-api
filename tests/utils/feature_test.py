import pytest

from pcapi.core.testing import override_features
from pcapi.models import ApiErrors
from pcapi.models.feature import FeatureToggle
from pcapi.utils.feature import feature_required


class FeatureRequiredTest:
    @override_features(WEBAPP_SIGNUP=True)
    def when_feature_is_activated_dont_raise_error(self):
        # given
        @feature_required(FeatureToggle.WEBAPP_SIGNUP)
        def decorated_function():
            return "expected result"

        # when
        result = decorated_function()

        # then
        assert result == "expected result"

    @override_features(WEBAPP_SIGNUP=False)
    def when_feature_is_not_activated_raise_an_error(self):
        # given
        @feature_required(FeatureToggle.WEBAPP_SIGNUP)
        def decorated_function():
            return "expected result"

        # then
        with pytest.raises(ApiErrors) as errors:
            decorated_function()
        assert errors.value.status_code == 403
        assert errors.value.errors == {"Forbidden": ["You don't have access to this page or resource"]}

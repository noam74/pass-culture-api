from pcapi.models.api_errors import ApiErrors


class AlreadyActivatedException(ApiErrors):
    def __init__(self) -> None:
        super().__init__({"user": ["Cet utilisateur a déjà crédité son pass Culture"]})

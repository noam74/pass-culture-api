from pcapi.models.api_errors import ApiErrors


class AlreadyActivatedException(ApiErrors):
    def __init__(self) -> None:
        super().__init__({"user": ["Cet utilisateur a déjà crédité son pass Culture"]})


class NoMatchingGrantForUserException(ApiErrors):
    def __init__(self, age) -> None:
        super().__init__({"user": [f"Aucune subvention n'existe pour l'âge de l'utilisateur ({age} ans)"]})

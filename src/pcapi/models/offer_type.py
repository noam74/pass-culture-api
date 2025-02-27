from enum import Enum


class CategoryType(Enum):
    EVENT = "Event"
    THING = "Thing"


class EventType(Enum):
    def as_dict(self) -> dict:
        dict_value = {
            "type": CategoryType.EVENT.value,
            "value": str(self),
        }
        dict_value.update(self.value)
        return dict_value

    ACTIVATION = {
        "proLabel": "Pass Culture : activation évènementielle",
        "appLabel": "Pass Culture : activation évènementielle",
        "offlineOnly": True,
        "onlineOnly": False,
        "sublabel": "Activation",
        "description": "Activez votre pass Culture grâce à cette offre",
        "conditionalFields": [],
        "isActive": True,
    }
    CINEMA = {
        "proLabel": "Cinéma - projections et autres évènements",
        "appLabel": "Cinéma",
        "offlineOnly": True,
        "onlineOnly": False,
        "sublabel": "Regarder",
        "description": "Action, science-fiction, documentaire ou comédie sentimentale ? En salle, en plein air ou bien au chaud chez soi ? Et si c’était plutôt cette exposition qui allait faire son cinéma ?",
        "conditionalFields": ["author", "visa", "stageDirector"],
        "isActive": True,
    }
    CONFERENCE_DEBAT_DEDICACE = {
        "proLabel": "Conférences, rencontres et découverte des métiers",
        "appLabel": "Conférences, rencontres et découverte des métiers",
        "offlineOnly": True,
        "onlineOnly": False,
        "sublabel": "Rencontrer",
        "description": "Parfois une simple rencontre peut changer une vie...",
        "conditionalFields": ["speaker"],
        "isActive": True,
    }
    JEUX = {
        "proLabel": "Jeux - événements, rencontres, concours",
        "appLabel": "Jeux - événement, rencontre ou concours",
        "offlineOnly": True,
        "onlineOnly": False,
        "sublabel": "Jouer",
        "description": "Résoudre l’énigme d’un jeu de piste dans votre ville ? Jouer en ligne entre amis ? Découvrir cet univers étrange avec une manette ?",
        "conditionalFields": [],
        "isActive": True,
    }
    MUSIQUE = {
        "proLabel": "Musique - concerts, festivals",
        "appLabel": "Concert ou festival",
        "offlineOnly": True,
        "onlineOnly": False,
        "sublabel": "Écouter",
        "description": "Plutôt rock, rap ou classique ? Sur un smartphone avec des écouteurs ou entre amis au concert ?",
        "conditionalFields": ["author", "musicType", "performer"],
        "isActive": True,
    }
    MUSEES_PATRIMOINE = {
        "proLabel": "Musées, galeries, patrimoine - visites ponctuelles, visites guidées, activités spécifiques",
        "appLabel": "Musée, arts visuels et patrimoine",
        "offlineOnly": True,
        "onlineOnly": False,
        "sublabel": "Regarder",
        "description": "Action, science-fiction, documentaire ou comédie sentimentale ? En salle, en plein air ou bien au chaud chez soi ? Et si c’était plutôt cette exposition qui allait faire son cinéma ?",
        "conditionalFields": [],
        "isActive": True,
    }
    PRATIQUE_ARTISTIQUE = {
        "proLabel": "Pratique artistique - séances d'essai et stages ponctuels",
        "appLabel": "Pratique artistique",
        "offlineOnly": True,
        "onlineOnly": False,
        "sublabel": "Pratiquer",
        "description": "Jamais osé monter sur les planches ? Tenter d’apprendre la guitare, le piano ou la photographie ? Partir cinq jours découvrir un autre monde ? Bricoler dans un fablab, ou pourquoi pas, enregistrer votre premier titre ?",
        "conditionalFields": ["speaker"],
        "isActive": True,
    }
    SPECTACLE_VIVANT = {
        "proLabel": "Spectacle vivant",
        "appLabel": "Spectacle",
        "offlineOnly": True,
        "onlineOnly": False,
        "sublabel": "Applaudir",
        "description": "Suivre un géant de 12 mètres dans la ville ? Rire aux éclats devant un stand up ? Rêver le temps d’un opéra ou d’un spectacle de danse ? Assister à une pièce de théâtre, ou se laisser conter une histoire ?",
        "conditionalFields": ["author", "showType", "stageDirector", "performer"],
        "isActive": True,
    }


class ThingType(Enum):
    def as_dict(self):
        dict_value = {
            "type": CategoryType.THING.value,
            "value": str(self),
        }
        dict_value.update(self.value)

        return dict_value

    ACTIVATION = {
        "proLabel": "Pass Culture : activation en ligne",
        "appLabel": "Pass Culture : activation en ligne",
        "offlineOnly": False,
        "onlineOnly": True,
        "sublabel": "Activation",
        "description": "Activez votre pass Culture grâce à cette offre",
        "conditionalFields": [],
        "isActive": True,
        "canExpire": True,
    }
    AUDIOVISUEL = {
        "proLabel": "Audiovisuel - films sur supports physiques et VOD",
        "appLabel": "Film",
        "offlineOnly": False,
        "onlineOnly": False,
        "sublabel": "Regarder",
        "description": "Action, science-fiction, documentaire ou comédie sentimentale ? En salle, en plein air ou bien au chaud chez soi ? Et si c’était plutôt cette exposition qui allait faire son cinéma ?",
        "conditionalFields": [],
        "isActive": True,
        "canExpire": True,
    }
    CINEMA_ABO = {
        "proLabel": "Cinéma - cartes d'abonnement",
        "appLabel": "Carte d'abonnement cinéma",
        "offlineOnly": True,
        "onlineOnly": False,
        "sublabel": "Regarder",
        "description": "Action, science-fiction, documentaire ou comédie sentimentale ? En salle, en plein air ou bien au chaud chez soi ? Et si c’était plutôt cette exposition qui allait faire son cinéma ?",
        "conditionalFields": [],
        "isActive": True,
        "canExpire": True,
    }
    CINEMA_CARD = {
        "proLabel": "Cinéma - vente à distance",
        "appLabel": "Cinéma",
        "offlineOnly": False,
        "onlineOnly": True,
        "sublabel": "Regarder",
        "description": "Action, science-fiction, documentaire ou comédie sentimentale ? En salle, en plein air ou bien au chaud chez soi ? Et si c’était plutôt cette exposition qui allait faire son cinéma ?",
        "conditionalFields": [],
        "isActive": True,
        "canExpire": True,
    }
    JEUX = {
        "proLabel": "Jeux (support physique)",
        "appLabel": "Support physique",
        "offlineOnly": True,
        "onlineOnly": False,
        "sublabel": "Jouer",
        "description": "Résoudre l’énigme d’un jeu de piste dans votre ville ? Jouer en ligne entre amis ? Découvrir cet univers étrange avec une manette ?",
        "conditionalFields": [],
        "isActive": False,
        "canExpire": True,
    }
    JEUX_VIDEO_ABO = {
        "proLabel": "Jeux - abonnements",
        "appLabel": "Jeux - abonnements",
        "offlineOnly": False,
        "onlineOnly": True,
        "sublabel": "Jouer",
        "description": "Résoudre l’énigme d’un jeu de piste dans votre ville ? Jouer en ligne entre amis ? Découvrir cet univers étrange avec une manette ?",
        "conditionalFields": [],
        "isActive": True,
        "canExpire": True,
    }
    JEUX_VIDEO = {
        "proLabel": "Jeux vidéo en ligne",
        "appLabel": "Jeu vidéo",
        "offlineOnly": False,
        "onlineOnly": True,
        "sublabel": "Jouer",
        "description": "Résoudre l’énigme d’un jeu de piste dans votre ville ? Jouer en ligne entre amis ? Découvrir cet univers étrange avec une manette ?",
        "conditionalFields": [],
        "isActive": True,
        "canExpire": True,
    }
    LIVRE_AUDIO = {
        "proLabel": "Livres audio numériques",
        "appLabel": "Livre audio numérique",
        "offlineOnly": False,
        "onlineOnly": True,
        "sublabel": "Lire",
        "description": "S’abonner à un quotidien d’actualité ? À un hebdomadaire humoristique ? À un mensuel dédié à la nature ? Acheter une BD ou un manga ? Ou tout simplement ce livre dont tout le monde parle ?",
        "conditionalFields": ["author"],
        "isActive": True,
        "canExpire": False,
    }
    LIVRE_EDITION = {
        "proLabel": "Livres papier ou numérique, abonnements lecture",
        "appLabel": "Livre ou carte lecture",
        "offlineOnly": False,
        "onlineOnly": False,
        "sublabel": "Lire",
        "description": "S’abonner à un quotidien d’actualité ? À un hebdomadaire humoristique ? À un mensuel dédié à la nature ? Acheter une BD ou un manga ? Ou tout simplement ce livre dont tout le monde parle ?",
        "conditionalFields": ["author", "isbn"],
        "isActive": True,
        "canExpire": True,
    }
    MUSEES_PATRIMOINE_ABO = {
        "proLabel": "Musées, galeries, patrimoine - entrées libres, abonnements",
        "appLabel": "Musée, arts visuels et patrimoine",
        # MUSEES_PATRIMOINE_ABO can be now offline or online, it is not a problem because front is now using subcategory online_offline_platform parameter
        "offlineOnly": False,
        "onlineOnly": False,
        "sublabel": "Regarder",
        "description": "Action, science-fiction, documentaire ou comédie sentimentale ? En salle, en plein air ou bien au chaud chez soi ? Et si c’était plutôt cette exposition qui allait faire son cinéma ?",
        "conditionalFields": [],
        "isActive": True,
        "canExpire": True,
    }
    MUSIQUE_ABO = {
        "proLabel": "Musique - cartes d'abonnement concerts",
        "appLabel": "Abonnements concerts",
        "offlineOnly": True,
        "onlineOnly": False,
        "sublabel": "Écouter",
        "description": "Plutôt rock, rap ou classique ? Sur un smartphone avec des écouteurs ou entre amis au concert ?",
        "conditionalFields": ["musicType"],
        "isActive": True,
        "canExpire": True,
    }
    MUSIQUE = {
        "proLabel": "Musique - supports physique ou en ligne",
        "appLabel": "Musique",
        "offlineOnly": False,
        "onlineOnly": False,
        "sublabel": "Écouter",
        "description": "Plutôt rock, rap ou classique ? Sur un smartphone avec des écouteurs ou entre amis au concert ?",
        "conditionalFields": ["author", "musicType", "performer"],
        "isActive": True,
        "canExpire": True,
    }
    OEUVRE_ART = {
        "proLabel": "Vente d'œuvres d'art",
        "appLabel": "Œuvre d’art",
        "offlineOnly": True,
        "onlineOnly": False,
        "sublabel": "Regarder",
        "description": "Action, science-fiction, documentaire ou comédie sentimentale ? En salle, en plein air ou bien au chaud chez soi ? Et si c’était plutôt cette exposition qui allait faire son cinéma ?",
        "conditionalFields": [],
        "isActive": True,
        "canExpire": True,
    }
    PRATIQUE_ARTISTIQUE_ABO = {
        "proLabel": "Pratique artistique - abonnements, cours",
        "appLabel": "Pratique artistique",
        "offlineOnly": True,
        "onlineOnly": False,
        "sublabel": "Pratiquer",
        "description": "Jamais osé monter sur les planches ? Tenter d’apprendre la guitare, le piano ou la photographie ? Partir cinq jours découvrir un autre monde ? Bricoler dans un fablab, ou pourquoi pas, enregistrer votre premier titre ?",
        "conditionalFields": ["speaker"],
        "isActive": True,
        "canExpire": True,
    }
    PRESSE_ABO = {
        "proLabel": "Presse en ligne - abonnements",
        "appLabel": "Presse en ligne",
        "offlineOnly": False,
        "onlineOnly": True,
        "sublabel": "Lire",
        "description": "S’abonner à un quotidien d’actualité ? À un hebdomadaire humoristique ? À un mensuel dédié à la nature ? Acheter une BD ou un manga ? Ou tout simplement ce livre dont tout le monde parle ?",
        "conditionalFields": [],
        "isActive": True,
        "canExpire": False,
    }
    INSTRUMENT = {
        "proLabel": "Vente et location d’instruments de musique",
        "appLabel": "Instrument de musique",
        "offlineOnly": True,
        "onlineOnly": False,
        "sublabel": "Pratiquer",
        "description": "Jamais osé monter sur les planches ? Tenter d’apprendre la guitare, le piano ou la photographie ? Partir cinq jours découvrir un autre monde ? Bricoler dans un fablab, ou pourquoi pas, enregistrer votre premier titre ?",
        "conditionalFields": [],
        "isActive": True,
        "canExpire": True,
    }
    MATERIEL_ART_CREA = {
        "proLabel": "Matériel arts créatifs",
        "appLabel": "Matériel arts créatifs",
        "offlineOnly": True,
        "onlineOnly": False,
        "sublabel": "",
        "description": "",
        "conditionalFields": [],
        "isActive": True,
        "canExpire": True,
    }
    SPECTACLE_VIVANT_ABO = {
        "proLabel": "Spectacle vivant - cartes d'abonnement",
        "appLabel": "Abonnement spectacles",
        "offlineOnly": True,
        "onlineOnly": False,
        "sublabel": "Applaudir",
        "description": "Suivre un géant de 12 mètres dans la ville ? Rire aux éclats devant un stand up ? Rêver le temps d’un opéra ou d’un spectacle de danse ? Assister à une pièce de théâtre, ou se laisser conter une histoire ?",
        "conditionalFields": ["showType"],
        "isActive": True,
        "canExpire": True,
    }


# The as_dict() method is still needed because keys "type" and "value" are used...
ALL_OFFER_TYPES_DICT = {str(t): t.as_dict() for t in list(ThingType) + list(EventType)}

EXPIRABLE_OFFER_TYPES = {str(offer_type) for offer_type in ThingType if offer_type.value.get("canExpire", False)}
PERMANENT_OFFER_TYPES = {str(offer_type) for offer_type in ThingType if not offer_type.value.get("canExpire", False)}


class ProductType:
    @classmethod
    def is_thing(cls, name: str) -> bool:
        for possible_type in list(ThingType):
            if str(possible_type) == name:
                return True

        return False

    @classmethod
    def is_book(cls, typ: str) -> bool:
        return typ == str(ThingType.LIVRE_EDITION)

    @classmethod
    def is_event(cls, name: str) -> bool:
        for possible_type in list(EventType):
            if str(possible_type) == name:
                return True

        return False


class Category(Enum):
    CINEMA = ["Cinéma", "Carte d'abonnement cinéma"]
    CONFERENCE = ["Conférences, rencontres et découverte des métiers"]
    INSTRUMENT = ["Instrument de musique"]
    JEUX_VIDEO = [
        "Jeux - événement, rencontre ou concours",
        "Jeux - abonnements",
        "Jeu vidéo",
        "Support physique",
    ]
    FILM = ["Film"]
    LECON = ["Pratique artistique"]
    LIVRE = ["Livre audio numérique", "Livre ou carte lecture"]
    MUSIQUE = ["Concert ou festival", "Abonnements concerts", "Musique"]
    PRESSE = ["Presse en ligne"]
    SPECTACLE = ["Spectacle", "Abonnement spectacles"]
    VISITE = ["Musée, arts visuels et patrimoine"]
    MATERIEL_ART_CREA = ["Matériel arts créatifs"]


CategoryNameEnum = Enum("CategoryNameEnum", {category.name: category.name for category in list(Category)})

CATEGORIES_LABEL_DICT = {label: category.name for category in list(Category) for label in category.value}

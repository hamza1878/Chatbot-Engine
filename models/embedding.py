"""
Moviroo AI Chatbot - Embedding Service
Multilingual SentenceTransformer: EN / FR / AR / Franco-Arabic
"""
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Union
import logging
import torch

from config import settings

logger = logging.getLogger(__name__)

FRANCO_MAP = {
    "machkel":    "مشكل problem problème",
    "mochkla":    "مشكلة problem problème",
    "fil":        "في in dans",
    "mafihch":    "ما فيش no rien",
    "makanch":    "ما كانش nothing rien",
    "barcha":     "برشا many beaucoup",
    "kifech":     "كيفاش how comment",
    "wakt":       "وقت time temps",
    "flous":      "فلوس money argent",
    "bel mouch":  "مجاناً free gratuit",
    "mte3i":      "مالي my mon",
    "mte3ek":     "مالك your ton",
    "9bel":       "قبل before avant",
    "ba3d":       "بعد after après",
    "d9ay9":      "دقائق minutes minutes",
    "lazem":      "يجب must il faut",
    "tnajam":     "تنجم can peut",
    "walla":      "أو or ou",
    "mbaa3d":     "بعدين then ensuite",
    "ken":        "إذا if si",
    "hne":        "هنا here ici",
    "heka":       "هذا this ceci",
    "okhra":      "أخرى other autre",
    "jdid":       "جديد new nouveau",
    "ahla":       "أهلاً hello bonjour",
    "salam":      "سلام hello bonjour",
    "paiement":   "دفع payment paiement",
    "carte":      "بطاقة card carte",
    "rséd":       "رصيد balance solde",
    "khassemni":  "خصموني charged débité",
    "mraytein":   "مرتين twice deux fois",
    "remboursement": "استرداد refund remboursement",
    "verifi":     "تحقق check vérifier",
    "jrreb":      "جرب try essayer",
    "réservation": "حجز booking réservation",
    "course":     "رحلة ride course",
    "trajet":     "مسار trip trajet",
    "chauffeur":  "سائق driver chauffeur",
    "sayi9":      "سائق driver chauffeur",
    "karhba":     "سيارة car voiture",
    "annuli":     "إلغاء cancel annuler",
    "na9ra":      "أحجز book réserver",
    "nsit":       "نسيت forgot oublié",
    "password":   "كلمة المرور password mot de passe",
    "compte":     "حساب account compte",
    "msakker":    "مسكر locked bloqué",
    "mow9ouf":    "موقوف suspended suspendu",
    "nconnecti":  "أتصل login connecter",
    "nbeddel":    "أبدل change changer",
    "nraja3":     "أرجع reset réinitialiser",
    "app":        "تطبيق application app",
    "crash":      "تعطل crash plantage",
    "updati":     "حديث update mise à jour",
    "msah":       "امسح clear effacer",
    "cache":      "ذاكرة مؤقتة cache cache",
    "sakker":     "أغلق close fermer",
    "iftah":      "افتح open ouvrir",
    "doboz":      "اضغط press appuyer",
    "dakhel":     "ادخل enter entrer",
    "rou7":       "اذهب go aller",
    "bta2":       "بطيء slow lent",
    "ma tkhademch": "لا تعمل not working ne fonctionne pas",
    "ta5ar":      "تأخر late en retard",
    "ta2kher":    "تأخر delay retard",
    "teba3":      "تتبع track suivre",
    "stanet":     "انتظرت waited j'ai attendu",
    "n3ayyem":    "أقيّم rate noter",
    "nraport":    "أبلغ report signaler",
    "7kilu":      "اتصل به call him appeler",
    "khayef":     "خائف scared peur",
    "7aditha":    "حادثة accident accident",
    "salamtek":   "سلامتك safety sécurité",
    "code promo": "كود خصم promo code code promo",
    "m9adda":     "منتهي expired expiré",
    "ok ms":      "حسناً okay d'accord",
    "na3awnek":   "أساعدك I help you je t'aide",
    "mte2sefin":  "آسفون sorry désolés",
    "klem":       "كلم contact contacter",
    "support":    "دعم support support",
    "signali":    "أبلغ report signaler",
    "3awnek":     "مساعدة help aider",
}


class EmbeddingService:
    def __init__(self):
        self.model_name = settings.embedding_model
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.dimension = settings.embedding_dimension
        logger.info(f"EmbeddingService — model={self.model_name} device={self.device}")

    def load_model(self):
        try:
            self.model = SentenceTransformer(self.model_name, device=self.device)
            logger.info(f"Model loaded — dim={self.model.get_sentence_embedding_dimension()}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise

    def preprocess(self, text: str) -> str:
        """
        Augment Franco-Arabic text with AR + EN + FR translations.

        "nsit el password"
        → "nsit el password  نسيت forgot oublié  كلمة المرور password mot de passe"

        The model knows AR/EN/FR natively — augmentation bridges the franco gap.
        We APPEND translations, never replace, so original structure is preserved.
        """
        if not text:
            return ""
        text = " ".join(text.split())
        text_lower = text.lower()
        augments = []
        for franco, translation in FRANCO_MAP.items():
            if franco in text_lower:
                augments.append(translation)
        if augments:
            text = text + "  " + "  ".join(augments)
        return text

    def encode(self, texts: Union[str, List[str]], normalize: bool = True) -> np.ndarray:
        if self.model is None:
            self.load_model()
        if isinstance(texts, str):
            texts = [texts]
        texts = [self.preprocess(t) for t in texts]
        return self.model.encode(
            texts,
            normalize_embeddings=normalize,
            show_progress_bar=False,
            convert_to_numpy=True,
            batch_size=32,
        )

    def encode_single(self, text: str, normalize: bool = True) -> np.ndarray:
        return self.encode([text], normalize=normalize)[0]

    def get_dimension(self) -> int:
        if self.model is None:
            return self.dimension
        return self.model.get_sentence_embedding_dimension()


embedding_service = EmbeddingService()

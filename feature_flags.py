# feature_flags.py
# NinaOS Feature Flags System V1.0
# Ļauj ieslēgt/izslēgt jaunas funkcijas bez klientu traucēšanas

import os
import json
from datetime import datetime

class FeatureFlags:
    def __init__(self):
        self.flags = {
            # Pamata flags
            "new_memory_system": False,           # Jaunā super atmiņa
            "document_intelligence_v2": False,    # Uzlabota dokumentu apstrāde
            "canary_testing": False,              # Testēšana uz nelielu lietotāju daļu
            "premium_features": True,             # Premium iespējas
            "multi_channel_memory": False,        # Atmiņa no Telegram + Web + WhatsApp
            "zero_downtime_mode": True,           # Graceful updates
        }
        
        # Lietotāju specifiski flagi (piemēram testētājiem)
        self.user_flags = {}  # user_id -> {flag_name: True/False}

    def is_enabled(self, flag_name: str, user_id=None) -> bool:
        """Pārbauda, vai funkcija ir ieslēgta"""
        if flag_name not in self.flags:
            return False

        # Globālais flags
        enabled = self.flags.get(flag_name, False)

        # Lietotāja specifisks overrides (piemēram testētājiem)
        if user_id:
            user_override = self.user_flags.get(str(user_id), {})
            if flag_name in user_override:
                return user_override[flag_name]

        return enabled

    def enable(self, flag_name: str, user_id=None):
        """Ieslēdz funkciju globāli vai konkrētam lietotājam"""
        if user_id:
            if str(user_id) not in self.user_flags:
                self.user_flags[str(user_id)] = {}
            self.user_flags[str(user_id)][flag_name] = True
            print(f"✅ Feature '{flag_name}' enabled for user {user_id}")
        else:
            self.flags[flag_name] = True
            print(f"✅ Feature '{flag_name}' enabled globally")

    def disable(self, flag_name: str, user_id=None):
        """Izslēdz funkciju"""
        if user_id:
            if str(user_id) in self.user_flags:
                self.user_flags[str(user_id)][flag_name] = False
        else:
            self.flags[flag_name] = False
            print(f"❌ Feature '{flag_name}' disabled globally")

    def get_all_flags(self):
        """Atgriež visus flagus"""
        return {
            "global": self.flags,
            "users": self.user_flags
        }

# Globāls objekts
feature_flags = FeatureFlags()

# Piemērs lietošanai:
# if feature_flags.is_enabled("new_memory_system", user_id):
#     # Jaunā loģika
# else:
#     # Vecā loģika

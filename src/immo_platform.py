from enum import Enum
import os

from src.immo_data import ReportType

class ImmoPlatform(Enum):
    IMMONET = 'IMMONET'
    IMMOSCOUT = 'IMMOSCOUT'
    IMMOWELT = 'IMMOWELT'
    KLEINANZEIGEN = 'KLEINANZEIGEN'

    def get_url_replacement_string(self, type: ReportType):
        if type == ReportType.HOUSE:
            if self == ImmoPlatform.IMMONET:
                return '2'
            elif self == ImmoPlatform.IMMOSCOUT:
                return 'haus-kaufen'
            elif self == ImmoPlatform.IMMOWELT:
                return 'haeuser'
            elif self == ImmoPlatform.KLEINANZEIGEN:
                return 's-haus-kaufen'
        else:
            if self == ImmoPlatform.IMMONET:
                return '3'
            elif self == ImmoPlatform.IMMOSCOUT:
                return 'grundstueck-kaufen'
            elif self == ImmoPlatform.IMMOWELT:
                return 'grundstuecke'
            elif self == ImmoPlatform.KLEINANZEIGEN:
                return 's-grundstuecke-garten'
    
    def get_location(self):
        if self == ImmoPlatform.KLEINANZEIGEN:
            return os.getenv('ZIP_CODE')
        else:
            return os.getenv('LOCATION')
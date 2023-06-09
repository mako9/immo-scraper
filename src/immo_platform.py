from enum import Enum

from src.immo_data import ReportType

class ImmoPlatform(Enum):
    IMMONET = 'IMMONET'
    IMMOSCOUT = 'IMMOSCOUT'
    IMMOWELT = 'IMMOWELT'

    def get_url_replacement_string(self, type: ReportType):
        if type == ReportType.HOUSE:
            if self == ImmoPlatform.IMMONET:
                return '2'
            elif self == ImmoPlatform.IMMOSCOUT:
                return 'haus-kaufen'
            elif self == ImmoPlatform.IMMOWELT:
                return 'haeuser'
        else:
            if self == ImmoPlatform.IMMONET:
                return '3'
            elif self == ImmoPlatform.IMMOSCOUT:
                return 'grundstueck-kaufen'
            elif self == ImmoPlatform.IMMOWELT:
                return 'grundstuecke'
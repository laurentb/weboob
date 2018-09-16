
import weboob.capabilities.bank as OLD

# can't import *, __all__ is incomplete...
for attr in dir(OLD):
    globals()[attr] = getattr(OLD, attr)


__all__ = OLD.__all__


class CapBankWealth(CapBank):
    pass


class CapBankPockets(CapBank):
    pass


class Rate(BaseObject, Currency):
    pass

class CapCurrencyRate(CapBank):
    pass


class CapBankTransfer(OLD.CapBankTransfer):
    def transfer_check_label(self, old, new):
        from unidecode import unidecode

        return unidecode(old) == unidecode(new)


class CapBankTransferAddRecipient(CapBankTransfer, OLD.CapBankTransferAddRecipient):
    pass


Account.TYPE_MORTGAGE         = 17
Account.TYPE_CONSUMER_CREDIT  = 18
Account.TYPE_REVOLVING_CREDIT = 19

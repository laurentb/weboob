
import weboob.capabilities.bank as OLD

# can't import *, __all__ is incomplete...
for attr in dir(OLD):
    globals()[attr] = getattr(OLD, attr)


__all__ = OLD.__all__


class CapBankWealth(CapBank):
    pass


class CapBankPockets(CapBank):
    pass


Account.TYPE_MORTGAGE         = 17
Account.TYPE_CONSUMER_CREDIT  = 18
Account.TYPE_REVOLVING_CREDIT = 19


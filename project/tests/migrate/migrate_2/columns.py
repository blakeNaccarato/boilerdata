# flake8: noqa

from enum import auto

from boilerdata.enums import GetNameEnum


class Columns(GetNameEnum):
    V = auto()
    I = auto()
    T0 = auto()
    T1 = auto()
    T2 = auto()
    T3 = auto()
    T4 = auto()
    T5 = auto()
    Tw1 = auto()
    Tw2 = auto()
    Tw3 = auto()
    P = auto()
    T0cal = auto()
    T1cal = auto()
    T2cal = auto()
    T3cal = auto()
    T4cal = auto()
    T5cal = auto()
    Tw1cal = auto()
    Tw2cal = auto()
    Tw3cal = auto()
    Pcal = auto()
    Q01 = auto()
    Q12 = auto()
    Q23 = auto()
    Q34 = auto()
    Q45 = auto()
    T6ext = auto()
    dT_dx = auto()
    TLfit = auto()
    rvalue = auto()
    pvalue = auto()
    stderr = auto()
    intercept_stderr = auto()
    dT_dx_err = auto()
    k = auto()
    q = auto()
    q_err = auto()
    Q = auto()
    DT = auto()
    DT_err = auto()
    q_dupe = auto()
    q_err_dupe = auto()
    date = auto()
    rod = auto()
    coupon = auto()
    sample = auto()
    group = auto()
    monotonic = auto()
    joint = auto()

# flake8: noqa

from enum import auto

from boilerdata.models.enums import GetNameEnum


class AxesEnum(GetNameEnum):
    trial = auto()
    run = auto()
    time = auto()
    group = auto()
    rod = auto()
    coupon = auto()
    sample = auto()
    joint = auto()
    sixth_tc = auto()
    good = auto()
    new = auto()
    V = auto()
    I = auto()
    T_0 = auto()
    T_1 = auto()
    T_2 = auto()
    T_3 = auto()
    T_4 = auto()
    T_5 = auto()
    T_6 = auto()
    T_w1 = auto()
    T_w2 = auto()
    T_w3 = auto()
    P = auto()
    dT_dx = auto()
    dT_dx_err = auto()
    T_s = auto()
    T_s_err = auto()
    rvalue = auto()
    pvalue = auto()
    k = auto()
    q = auto()
    q_err = auto()
    Q = auto()
    DT = auto()
    DT_err = auto()

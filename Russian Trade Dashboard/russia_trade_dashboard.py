"""
Russia trade dashboard: 2021 exports (Russia's own reporting) vs. 2023 imports
(mirror data reported by partner countries, since Russia stopped publishing
detailed customs data after 2022).

Source: UN Comtrade via the World Bank's WITS SDMX API. See the "Methodology"
tab in this app for the exact queries used.

Single-file app: the cleaned data is embedded below (gzip+base64), and running
this file directly with plain `python` will relaunch itself under
`streamlit run` automatically -- see the bootstrap block right below.
"""

import base64
import gzip
import io
import os
import subprocess
import sys


def _in_streamlit_runtime():
    """True only when this script is already executing inside a live
    Streamlit server (i.e. it was launched via `streamlit run`)."""
    try:
        from streamlit.runtime import exists as _st_exists
        return _st_exists()
    except Exception:
        try:
            from streamlit.runtime.scriptrunner import get_script_run_ctx
            return get_script_run_ctx() is not None
        except Exception:
            return False


def _bootstrap():
    """Let people just run `python russia_trade_dashboard.py` (or double-click
    it) instead of having to remember `streamlit run ...`. If we're not
    already inside a Streamlit server, relaunch this same file under one."""
    if __name__ != "__main__" or _in_streamlit_runtime():
        return
    try:
        import streamlit  # noqa: F401
    except ImportError:
        print(
            "Streamlit isn't installed yet. Run this first:\n"
            "    pip install streamlit pandas numpy plotly\n"
            "...then run this file again."
        )
        sys.exit(1)
    script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(script_path)
    # Force this app's dark theme so its light text/chart colors always have
    # proper contrast. Without this, Streamlit auto-detects the OS/browser
    # light/dark setting and can render a light page behind our light text,
    # making it unreadable.
    try:
        st_config_dir = os.path.join(script_dir, ".streamlit")
        os.makedirs(st_config_dir, exist_ok=True)
        with open(os.path.join(st_config_dir, "config.toml"), "w") as f:
            f.write(
                "[theme]\n"
                'base = "dark"\n'
                'primaryColor = "#3987e5"\n'
                'backgroundColor = "#1a1a19"\n'
                'secondaryBackgroundColor = "#0d0d0d"\n'
                'textColor = "#ffffff"\n'
                'font = "sans serif"\n'
            )
    except OSError:
        pass  # non-fatal: the in-app CSS override below is the backup
    print("Launching the dashboard with Streamlit (this opens your browser)...")
    result = subprocess.run(
        [sys.executable, "-m", "streamlit", "run", script_path, *sys.argv[1:]],
        cwd=script_dir,
    )
    sys.exit(result.returncode)


_bootstrap()

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# --------------------------------------------------------------------------
# Palette - dark mode (validated data-viz dark steps: blue sequential,
# blue<->red diverging). This app is fixed to dark mode throughout, so
# every ink/surface role below is the dark-surface-validated value, not a
# light/dark pair.
# --------------------------------------------------------------------------
INK_PRIMARY = "#ffffff"
INK_SECONDARY = "#c3c2b7"
INK_MUTED = "#898781"
SURFACE = "#1a1a19"
PAGE_PLANE = "#0d0d0d"
GRIDLINE = "#2c2c2a"
BASELINE = "#383835"  # axis / zero-line role - distinct from gridline, still recessive
BORDER = "rgba(255,255,255,0.10)"
GOOD_TEXT = "#0ca30c"
BAD_TEXT = "#d03b3b"
ACCENT_ORANGE = "#d95926"  # categorical slot 2 (dark step) - "selected item" marker only, never for magnitude
ACCENT_BLUE = "#3987e5"  # categorical slot 1 (dark step) - positive-value bar fill
LANDCOLOR = "#333330"  # choropleth land tint on the dark surface - distinct from ocean (SURFACE) and gridlines

# Sequential blue: low value -> dark (recedes toward the dark surface), high
# value -> light (pops). This is the light-mode ramp reversed - on a light
# surface low values recede to light; on a dark surface they recede to dark.
BLUE_STEPS = [
    "#0d366b", "#104281", "#184f95", "#1c5cab", "#256abf", "#2a78d6",
    "#3987e5", "#5598e7", "#6da7ec", "#86b6ef", "#9ec5f4", "#b7d3f6", "#cde2fb",
]
SEQ_BLUE = [[i / (len(BLUE_STEPS) - 1), c] for i, c in enumerate(BLUE_STEPS)]


def _diverging_scale():
    # blue <-> red, dark neutral midpoint, brightening toward each extreme so
    # both poles stay legible against the dark surface.
    red_arm = ["#383835", "#5a3632", "#823b34", "#b23f3b", "#e66767"]
    blue_arm = ["#383835", "#2c4460", "#1c5cab", "#256abf", "#3987e5"]
    n = len(red_arm) - 1
    stops = []
    for i, c in enumerate(reversed(red_arm)):
        stops.append((0.5 * i / n, c))
    for i, c in enumerate(blue_arm[1:], start=1):
        stops.append((0.5 + 0.5 * i / n, c))
    stops = sorted(set(stops), key=lambda t: t[0])
    return [[p, c] for p, c in stops]


DIV_BLUE_RED = _diverging_scale()

LEGACY_NOTE_CODES = {"ROM", "SER", "SUD", "TMP", "ZAR", "MNT"}

st.set_page_config(
    page_title="Russia trade shift: 2021 -> 2023",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------------------------------
# Embedded data (gzip + base64 of the cleaned WITS export/import table) so
# this dashboard ships as a single .py file with no sidecar CSV/JSON.
# --------------------------------------------------------------------------
_TRADE_DATA_B64 = """
H4sIAJpFhmoC/5WdW3PcRpK27zdi/0OHbzwTUexFHVAFxF5RpEzJ4kHDgzzWzQZE9kg9Jrs1TdJe6td/z5sAmvRGQPO1Z9IjscFG
oSrzzTdPmIP1zcIt79fRHawfVw+bJ3fNT/5ntX5YuA/d7eMiVMG7iy/dpv/T+LO4/Vl03af7/7n+0q0+L9zX64fxj/cP3cPj/X/+
x8GbU2fyZbnqnMtNLm1IzbxqXDX3sa2r0LapbppSgvOhDVVdlzJvWz6OlW+qXNVNKG0KxfHHkGNo5613TTP3oWnbGOrSVlWd3fvN
4n6xepgtV7NP64cvs6dFt2EBp8eHzmTx8GWxue1WN/fOpeATd67nPnOfqqkz9wm+DTG3vnF18TmXME/2qY+xjjGFpk41a3V7MfOX
WId5bvt/sttr8jxFfi/Eqo2p8ZPrOXx95SRHi81dt3pyLrQ51Tm18yrpblpHbkuTm+gTC0gh+bpJ82xrqdq2KiXVwddVw0VuL9Sp
SlVO89iwipo1hdiUUOfQNmVqEZdX587kcfPb8mnBIngkfoMNKbpNHXPhNsXHpvZNdKnmyWuesXgdW5Vrn0LwodRtLs63vnAsfl4n
x67VdWz4vdI0Fds5tYRXx+fOZHHbbR45kxB9rGIT5igCS0i5bWJVcbjsev/wjqd9cdGer/TDs9Xtk75cCjr7y2qtP8TZ3XKzWW9m
N91D99f//I+jV+dOcrVaPixuZu+Wq8836zvuGUJJ2bfz0to965BSyVXb1DHE6Dj3qk6DklRVE1JuUpMjG862sBo0xteZTY9ur23m
ySc0sq59Cbma3Py3l/vO5KG75fz5joZDRttq3SaymRVaHmr2mzNN+kFu540djEdpm7rOJaFnbO6eTw32pF0vvS6yLOwnhOyDbxr9
JNZTK3m3/9GZdN+6375gsiuW06Q2Nj4Oyh8Lz1fJzKSPrfO5f+Z5Lv3HDbeqqsyPS651QJXPfCyj1D+eJfJoKBBbk7ClXDdTy7m6
2Hcm/SldACELFMNLEzmVeWMGEnOVeHQ0ti46hdRWnFo1r6NtEIbtk8dk2NJaN28ShykwGYyV/QnzWNDt4LkOFZs8qXdn507yw7v1
ZtG52fni63z2l4v1I5fYj/76A8vLTYvBYxbelpeiL57TQPczaNFwCLFu5rV9GqqCpbU+1PpjwWLBLlY8x5JTwYYTZp1y4YjRqYll
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
"""

_META = {
    "world_exports_2021_usd_thousand": 492313790.7,
    "world_imports_2023_usd_thousand": 428107966.84
}


@st.cache_data
def load_data():
    raw = gzip.decompress(base64.b64decode(_TRADE_DATA_B64))
    df = pd.read_csv(io.StringIO(raw.decode("utf-8")))
    return df, _META


df, meta = load_data()

WLD_EXP = meta["world_exports_2021_usd_thousand"] / 1000  # -> US$ million
WLD_IMP = meta["world_imports_2023_usd_thousand"] / 1000

df["Value2021_m"] = df["Value2021"] / 1000  # US$ million
df["Value2023_m"] = df["Value2023"] / 1000
df["abs_change_m"] = df["abs_change"] / 1000


# --------------------------------------------------------------------------
# Russia's IMPORTS data (mirror image of the exports dataset above): 2021 is
# Russia's own reported imports, 2023 is partner countries' own reported
# exports TO Russia (mirror data, same reason as the exports side - Russia
# stopped publishing detailed customs data after 2022). Used only by the
# flow toggle in the "Change map" / "Top movers" tabs - see Methodology for
# the exact source queries.
# --------------------------------------------------------------------------
_TRADE_IMPORTS_DATA_B64 = """
H4sIAJpFhmoC/5WdXXMTSbau70/E+Q+KvpnuiKROZWZVZlbsK2M+x9gwtoFpbnYUtsZosCVGlugNv36/z6qSMe6oPiGiVzdtElVW
5vp416cOV5dzt7hdRXe42i4362/uQj/57+VqM3fv+uvtPNTBu7NP/Xr43e5n8e5n0fUfb//74lO/vJq7Lxeb3W9vN/1me/t//8/B
s+fO6F9X+oOFfrx0rskhVL7EXJyvUl26mLoUU/K57tL8Ud26uqqNHt1b+sjX/Oj18vrbbLGcsaHZr8sVv4mzm8V6vVrPLvtN/5ue
+vy1M1pera5753zXdVX0vgsuVcWHOoboYxtyDJ2el1zSj0Od2saFqi116rpS55LrNvLnWc/uYqiazoeU3KMuVanNxeembVufY+fe
rOe38+WGfX1cbT7Nvs37NW//6rEzuv6ol2cjqaSm8npV79pKf7+LXd2mLusFG3vzLld1SBx21J/nkOs6NG3wpY7jTlJOufJNXZfS
8Us/09s1odGnJt+ktq6nN3TyxBktL1frtTbUdFVObQpcRNfqLhrflBiS/mWPC21TNTqL6DqdkO4hFj1W/w55+PO6qbJvfd2Nv4pr
vK9iW9q68SF2OufJzZw+ddDb5WIzv5wdrPuPs6e6yH4zv3Uu5BTrWHVN7Qu8oLfS3nzX5pp/N3pQ04WYc9XGug2JNbqLttaioB2V
NvrsmuCTdl+1XR2b5Hwb2qoUvVVsm67JzfTexLPQ+kp/ulhyd7Xep9YxtLFpbEf6b+e1yVac1PrQJhd0v3Wr2ym+syW+5shy9qHT
v5omuEe5iZlT06Zb/V+suDgftaPclembOz12RuububFS9r5NvgowwXhCQUzQhBibUhrtIzZOx9E2oatCVw97FtdH3XFXUupC3Uog
Qu5iSYUDbpoSXOxClaI43ZcGMeimz+hM24Fu5uvFRb+cnfU3K+1MJ6zHZLEUUtQFyVOpm65OsEz5Idu7dfsI9vkzBz1bz5cXn2Zn
q+3m03y9nJ3P1+vFZrVewDl1FUMO6BYPZzbi6pjbOmckrPvx/N26vZ4vloDEE1fbftYvL2eP+/XH7SUMUukixHNJHNm2KfFIKZWH
j90t2+exb8+c0fZ2s+6v7fp1aTlVMXJBdvmtlIv+R3Ki845eNyumr0qXusJZ6H6TtIw2FLKXLjRtI/bT6bRVE2PXBlMkSVLVen16
Et+Gybt/e+6M2BH7CdKIbSmV2C2Z/tY2JGJ1IzHOsS6+cR5RDk0lvo8x25pWIl1Lx7V1V1ppOx1KaNssHYksS7YkZBiBKrRBstRK
1qSXy+SuPkijQN/n64/94t8YG0mg2F3ypjcNg9jqpDyvJwXjvTboZBmSqS1dybCxJumgpCC0QuoldNLcEi3dbG7EyvzS+7RVp/Nv
YgionTpNSsrjJy+d0Xa9XV4uHHooVpI6nyQtMkt6tZLaErvcda1ZpNAUXUXd6Le6kzpIVNiUHhjb0RBI6VQh5Cyr9ajESpeepKI8
P582SY+fvnJG8+urxfZGF6et1K0UiS5wOJ/SdgmN7jvpr4696Ed6QdmYIK0+rNHVNXpONvVRvC5JMiZrUnQcUrn6m9phrmITxAiy
pNl3TcrTuzpxRtJtAAQxANrJi29bHZLwQdb/SZf64XR8g8WrQzAzmrUdL+0pY9Q0fjid6HXlpU1FL2G/xOyym8V7yaX2mkJbpu/r
2YEz2q4/S/fPnvW3K+m1toJhozZVsh6XpST1+jI39shYp8rnLgWMqRhdqtfnVkfmdZfDneqYxd8SMNe0WtyEkqX6hUf8JEs/fv7E
GQlWXfeX89tP4h6AS4pV3WHTjF2jLHKjM9ZJe2n/e9rmp7V76JzHz0+d0fb6qjcRx/JKV3gZhoFRdKUoVp2kLJoEqHOtpDnGStZM
pnFQS7UQjyCJLrFu2gJaiegq2QZxu8GGFlOgH5Y2NJJA8Z40yNRxvNCOoP7TuodVZGpDXemhMYgVJJutXleqpM6yhdmUnI5AIEZ6
zrum6sQzUghSADFoV3Yvj2SGGvhIdzbCGKlC8bu4JjZZ9/xXGzpzRv2n/qa/dQakinCxPq8kX7pGmk1wKMaHVmBYts+NvHzhjFa3
QgBme17M19/nV6uvBlCKtFWuxJCtHwCTMIcgjnBLFjTw6JqkA67AB6Mq1NNsfSOJC0Hq2q5HXFk1TYtY8Yuf6YIkN20tTVS3mLfJ
83ily4Hm1/16y3m0ScvFFGJPnaepV92RuFLmMUoMm/t4/0+r9zmfVx+c0fx68X0uLSKBDIHL1DsL9GjrQo9FuiTZtUt7dkJMgvzS
G1nKpWl1DDmNOOWRrl8KXmZNzCBl3CVgbxL+/StNf/zWGc3XNwYKojRZaczTkX32PEc6RKZlUBp3L363bp8Xfi09Dq2uF1/NvZCF
EN/FRpzWIGGSfGlNcGppR1kIsmJ675K0IgchacxvkXh0gwPySKBdylUwEOYUI+i+BRe9Tq3IFk6++KnUJbTuvy+uZVb0S8/XwQMs
4DWpTMCGvA3QYMdmBHpl5HXIwwqBdtkV33atOFDrZNZypx9W4kXZf9hVB9VVrTCV7DdQR5pkekePnZHwWX+5EisKzkrIJQPyrZo6
mv4KUbLQDF7g3WX8WLjPbZzKfkGy8fPF7Ansf9tf97KxuDFyWeBDKX4xkThJvmOTfgbEu2X7PPRcD4Q+bc211uHg3uqJQUwgcKDz
kwNkZlM8GGS55Ne2cAe3IcWX5ASkNtifR6RcO3PIezEUqAsrwJSpQ3537oxW26/zzezl7bXUEhBcyFreFZ6HHLkWJOiRK1/fx9/D
on1e9704DFptbv/ozSuTmpLB0Y2h/4XDZJH0asJlSeBz4PkqAU0B5oKYctlSCtipVEwlP+IjhDNwVqNBYLlhUlDyJSVNeRJJHR48
c0b6M4Hy2cG/Bi/odP5l+/F6cYG3L7sjhaONJSE5KR8BRbl63eA7y3uTnya46xATwXlpatkmXNU8QrwaXwzzLvCiRZ38CSE8M6gx
TW/sxBnpgFBBeGBtEesJOg8A2Bu6bZFn7a/jvoXi5ODDK4Nh0N0XHiI4LqMtoCdhFE71MFgnbG5REKCm3N5aICZPyuHh4ZEzWl2s
bme/Hs2lnpdXv428goUIss66BDFlACJgmuW340P9LB93C/fgmMMXTx109sdiI69gYE+8Hd/WlZfxMWuPZyzTg6UXFJdgyB9xQmfS
VPgektjBe9avFo2WxczCf+JdYTxuST8rOsTOYK8Mi9hP5y0saDhw8mhevHJGnxbXMliC8mLFKkkrD7BOj5WCM9UX9VuxgfR0lj9f
Zx3QYOW9ZFyvI4gu64T+NOwrcydXTC5vhx2rWin8AELrBHKmGeeFmAb6ZHhCKzvBsga0G9DQQphJ3leQ4ySfR2hNjpNwJYdYedOf
QrSCEgJykjA5uQ5UKg3bcCC5GApvAyE/dL3sQF0wwFPbefnOGa0289nl315+XS3WcxwWDDUnPlyKPiQL+QpQ6KjaBnbmwuTxyuKk
bsQ5ugYxqfRZ54V3OgvpycORFwZo1q1lOSuAAH2qtl5Pq7zD41Nn1N/M16sV7krMXYUjiGvQICV4ldIvwsV+NLuxkueK19jgr+g5
8jhlg9o8irouWpa708kSYMx4ErLjBX6vJ52Dw9fPHfTL4Wp5tXKonuoXbC/IBRztsvYjxymgXvTf0bm8k6h7K/eRqdeSZmi1+vxD
jGXss7y/bHEXIU7xhxC/tHBqH0Cd3cK9HikpgVbXq5uPFnDQIqkgnLmRDeTrJax6g3eWxPkJjVUVWbEdIE5C5C3/EQtIb2HfhY7k
Hugn6LQkl17IU6eS0P9lWnJfHzuj1c1qvTIlhnFP8uzM++mAOrpvgmw/v/3dwn3e/o2kAOo/rmbv5utLxEBClbHVBTPqceNLDYIs
PyvNu3X7PO/0pTNa3W762anMml7QR6Cj7EIeZUoIIZfAP4J40oZOO5CVIqLTYfl9W2RpBQAEJZshrv+IWL9gjuCoJK7IG9O2Qfog
0WlF8PaxM9p+NJArccea1Q0eX5SaljRpc8R1f84e3F+6z+u/fe+Mtuv+ol+Zkyn0LkfdXMzi0XKRMFLrH1zu3cJ9HvdPKRPo03px
u5ETeQ9GyQAJP0hgGmLPiTCQ1HJ+GMgclu3zzN/Fu1D/7UaY5YcQZzRGKmBV6Xn9TVkS+QJS3vln1fFj5V6PfeOMvn0x51BWrB2c
rB3saCJZDNk0RFRoQExVC/JrBRZGGIWQtPCcjLXkuQxcJUTiZe8yQctdTkQOvS6+SBNFvFzpo0n2+iCIAH2fX3y6B98EfqTKC/G5
Yg6KtDg5DakZgTLipI4YpReWbsYAvMydXArp7K4j9SHpK52MHWic2Poj2QltPzckuwSr60mWf/L0rYOey4/sl99IhxDLt7gJIKMm
oEOkRzyPZ66Pl3uj25AGa8Up2aQgEsLH1+INcrSQnEyyML1cKm2LmJgMk6SXc2uJHk/v6O8vndG/Fx9X283C3bGCVCwoBHwtFCRc
WetRQaIw4Ou7P3Yn8z9GBok7BvGz9fxitb4Ubzw5PnBGq5vF0lROK38khhpe1D2SfRE00uukB77z3bo9OPHJyZEzmi9v+vVnFLig
ed1WhDqHAHYjFCPkqysGXxS9iSxHJ3wmn7rd6UDxgg4fp04cSRzUG/giMhs5+F0siegkWTIxfDuddnoik2I0nsF9b0IgLyU5CmkH
0KWIakLk4nsJaOukQrsq12JPyYkcSfntuH5BjlwzxLmifL4kb0gyMYS5CG3IR2lIkhB8A3NM7u2D7kZ0cH01t3igF8pKhp+8I9IC
t8mPEOYKXX6giO8t3eOSnh6+dUYXW3nwaxSxJKuRAZEojJeENInR5aTIfdHhyNgIw1d5l4aQF5eJHEtDChuQcpPARIKUuTOwnEgN
CAxIn+jupkM7T5//7oyuvn3ZiDmFHgXZiIzEMdLpxR3kAQuB++jwKFu9NUAlj0vkAMoTlR6R4Ep/PEpghErs1MYwBh6lyYRgfGmI
akvXT29IFtpovdis51xI1HsXT2pU8i03WJzryR6Lbx/YqbuV+9zG2QsHvZ/fbki6nfWf+rW54GGMs7WVJyslrK1jiT4/kNMfC/d6
6hsHnX2xeG8kBknGCtBuLhlWQqiiENaNIYoB6mCILtWjiyRPsgFfCPt7CQRqWdBO0oPHK3mxLCwRJoF/uQ4CrpN5r6dn587odrOy
NGwjhRqJUKUxD0cOHn2Q+VVIFcuGxLoUcg+j2mC1HCQxiP6yfBOXiWTVsnKWvid5QoZD7yS+jlontp9mg3NdC7T5tFh9YU+RpG8l
4xDGzLknj9Tin0pICuDLh46IYwrR/G5pgpiJbBKOSDurmnXS5o0SCmxzlVpwZuR65ctMOkjPXp44o8VydLdbIkCGHVMcDClKUrhN
/41iw+jEpzoSuaxlTFTXFlog5YfbKl0cMKat/rFkfgvcKXb/STAlk90ok8HJZ7JbRot/k3zT4Zhi14sLMEsgKeyIhEkforndwj34
9dmrI2fUX3/m9XfYavbrcX9NoP72NwPTuHjyMpw80GyxQJ07nuzPKOvewn32cHrgjNb98mKObROQafC8dXnGE41P+kwJTOzkiknp
kwjQ9VYSgjgCfJkxsm6Eo5rYDdYVGSMRSDpWFyC036LbJYyNFOgkxHp2+toZ9evV/B7aJLghXeXrMGaUZIEkCzAilQrR38Ob99fu
cxZnxw765XhxsV4t57eSkNmz+WU1O9vc4i3XeOaIhOxATdAGMcU5bx+i7GHdHs9+fvDYGclvk+4iECpDieuw80c5ZPIBRFiKgTbZ
Nzn9sIVOVIZJJqSVQRuKCB7xEcIWDVU4g6KwgKXl/eS01hSpTF3C88enDhrrbY4Wy6vL1Y1UWJMEXQhaSZWaeIoROk/9kz5R8Dk7
ZFSMGLLPY15PsFfH0bZCxJ0u3jdY0pacW9UBMOAOnSgWkaSxsGo9mf19/vS1M5qv1leWaUyYbyqxRmCNZs/UkQhak35pXCJo2wFd
xkobKSbtLRLikQWS++Asbik8N6YZyQPJXksUOmndhNM8ya/PXxw4o08WZC61lCcSscuaIRC5a0Ina4HnK2QnaC9DJJNtYUwp3NLq
YKVUu3b0fROQTCpOroFuUhhcYAzIVMhx1JPx0+cvxUDQ4uO6v970a2IfsElXnHSDpKSQMxGoiOaO3vf9d+v24VlpbqPtYmmggvSI
QG/T+B3mbci0d7GmUmRX7jGqq/uL93nosd4P6ofgDuZ4yLSHbOErISScne5PGZNh3T6POvmHg57+Z9tTMdRfz3avKgslS4O7rfsM
tZRlh73rxuzJ3VN36/Z56umhM1rP52hkcY7YgchMaMdCMflIwJMkWRaA0LnrxRoKKJoRPYqnqAOUo0H9TNuawyORTWOaMoyeryTH
R0K3jSU9y7RCOH3ijNbzIVMge0dyzsKYLfUVSf9pG3kaD5Dc3cK9juCVM9IRjMBAuFzusnx6QemRt1pwUSQdWXwK9znr3tJ9nnp+
7Ix02/ObnmpQ+WwUKiVKE0dXStpXMIPMtkV+ZdDksreJsik5C4I7iYIOobkRGsmdqKlZyPBeF1GdmFgBOyqZJs/7rfbx1vZyg90R
Cs/BsHok4RmtzjV3D7Nkw7J93vnt785o+83Ul9RRRdWhxQrFP7AGYeUcHgCeHwv3eNqLo+cO+uXFank1O+JfZwenbmZZhF8om/HS
xEK/9RjkIcuL1YBd5UrLoOjwZW98JWwpIG8mSM+hXJJETCDOKJ0nFQdOl9ruihWGxQEAimMo/4jT8OPFyRNntFpebtdUaQSAJXlB
PS5Vg/nEFyMhOtxxkvIGqSYKBCSCqcEYx0i5chwBckNoimCQJDHJCUhWNtcRiPaT1u7F6TsHHa5X/cYi2XqfLlXU7Y2CXgTDPTFk
yQEVHI5XbAhljwtkDiGSqoE0Px62MGRFMCgP9U5ST7IOUl54GxShgmOntnT+0hn1CwI7kZyPJI3Ai7dEYcNt6ZBi8yAIeLdyH4Z5
e+KMtsurfk1sK1AJJ2+s6M6HWoGMyifW2cmOeir0AGe6kFJGD0qHLiuUCYN1QzRdZjSIPzoDI41YvchvSolztA+eePmXT06c0fJy
hIfiRwHcXCpye4NiKkJlRQ6t5AZA3DpZBlk/ahlT2QUa0BCUGSUsB/aPmBWouyFGZ4o5hJZyb23yL9j1pVjVaHlpLmYTBKjErWUs
vEJ2yXRkIqVJnyysKv6sBY4bwYBhidA9JYPyZcVeqCl0VhL8zFTbE/vRzwqBVeE1Ka+C+plMdr+U4jZazwfVHSjPoUyvbQaGoMiA
4jPdkM4o6UWddGEiAJJAhiOOsypF/TnZ3SEHJG+uq3MVOzDTUOORKWKhXFqwtDENMbkt3Ru0tuIHAisDrBq2JAci2NvJpFJheq/C
4/7SPXj35ek/nNG6/49Vz9cWMqPEIJQouU2WuX6oWO8W7vOoMx03dDEeudXqVBY4cHQgyEEC90Wr6DWNJPAt5EkMC10huKqboAS5
Cd2uoqCTh00K396beGErpia6T7B7+pzPTp3R7bqfXwsQN9IK1Pm1YQx+6dUzWUZ5sC2V56Ba5HX40yDnVuqVSrS64P48Iovr0/gJ
j2JdES8XUm/IdKfp+rKX5wfOaNNff8Oz1SVLCqQ7hiSf2IXq1EAdPnFIMaGMq4A/1T5DpI5KVKpRait+4VISKJksPkEjnVIr0Q/F
whRZ8jOpyv9+cOyM+pveItZJ71MopW1HaEH1q3xoAvPCcYG8SqT8SddI2MPW4OcmHD29Cr6g/MTUiaOovBh7KmTjCPxrs4S/2jxd
bfH316fOaLW+RCZ06pFUjgzBuCM8t0boLYCzavo1xFUkUwxvt12D1pN7Yx0E7ei6RJIYqDdTHUPgOFb0X5iKk0BP8s7f35w4o/6L
CakeF7oGTdiZUhAE6ACqVg9JKakL0iC6K+GrVIaaZF9bkq8Qn9UZ66q1JS9lI+gLFs8WVEwd7hBtGQQLZBmmtnR08MEZ9d/7z5+G
piRBOVMJCbc3mv6Qp15TvCtRI1zSScEU7dEw0sBKwmuEDGRktTnBE8rgiSdVNPUIOpB4xG/WMcFjrRhgumDt6OmJM5ovv1meU7Av
UbAaxpC/XrORmibVmSh4bp2ebXXivjS7UJ90Ap0gwiJRd22uH+69WICGHNOtmFZxpEBtmq4tOHqu84G+ra++fb+fh5AGoZ0KpTI2
nugmKHDSVYqXyXA4VI8sehgDsNJCWqz372SMSKs3GYwvgcuUthtD6VrpT9EqcYP37XTzwdGLYwcdyltcXY7FAPJGKipA4q4YQCzf
EeYicU2JUyAL40me4VV6K9y3s8l5l0UsuTUQaq0QhXqQDPSRD5S7SSVwdHLgoLNNNTtabDa3Vpl7Mv+6EM7UhySOXbqlwQwHKo3F
Tyn87FLu1u1hH44k5dAvRyui/1b8MfvVWmJm9qPffkE/4miGUBElMP3YEDzqaHHr6FuQygpgBPHZwPPaBwWfQI4ovIE/WeTPC6Bq
f2Nw+pFAjUwdcBmJnI5dHL0/d0bbPwQtKbzKVMBbSa5HsLyshQyFfLsBWdKtUaEaO4omiSwKZlH/P1QQJJekOgQxmrGqX48OJO0o
Ji8WnorN5E29OnjtjPrV7M2TU/zPRDVCpJssVpIYrI+BasqEjCskQpUl0ZyUiwwHAUryR7uqFl0Yp6cjCla3k+VTWKdYxmmZ2sjj
E2c0/9gviQxKxCNImqyWPsNToy49VCgJ7mwfRcajQhPECiTaUWum6/HDPuDeaBhRZqTZWY1HkrCW0LIO1Ftx9+R+Tp3R4uOQ2qN9
rqItgV4GmaNEYk8SLdv9sMbi3tI9mPfV49+d0eIjuq4maU0jjnQTchuIKUphhfinGKyt2+dJhwcOQjxfbS9MW1jqg5C24FTx1FSY
mU71g3KOHwv3eeCRHig6Wy9mr/rlZx5YpC1zhSCOVhhg3ElZoVqs+gE5ClI+Vkw54oKkqzTHQ/CVBLrdMV0m4L5d+Ff6Pwo7Exul
jmtSFF+difGh+a1+uqK8T/aLnqtAsIdip84KPGXafj6Fu4X7HML5W2e02HzaDr2viar/tiLPFEZUiMMkbFij7yPNt7Kz5naPDSZ6
eblvchNkQCLdubhWHmxEsMSaUwUi9EdNTfdCO4lBXr39pzPa/s9cNmO7vpLwC+FYLL0ey89JLFL7RWRIkJoAg7xrbBRBOtpBsB7Z
yiukIZpdlowOGL0WGxhr1DuC4AXUK78KEzS5r3fiFajfWAG/1GzCBMntjWM2UXdCK6tunIIqK+AH9tChNZ4SPdICRdI80SpOKdwk
failZAPEWZLPIr2lSyaYOakGjg8OHfTLMWVPP0dxCE1WlLJQW05fY+TjG6nCMLZTFDkfUcgNFUURgB5Hlayc87tqZk97YfDUfHcE
WXWV1k5HZ9D0pk6d0Wq9urhYUW0piEU/Y7NrQ7I4p9iLxIAcOic4WYhc5DGYRKka7b9ZrkINgESDRIRet4umsd6CZqgBlVpNQVZG
ELiZBJDHTw6c0er6cvWVi/OAdTJEY/pSGjcD2ICpek1aMBsBReG5XTRXDnBLfRGPlwnEJ8qEdytutrFogZC1VCEpNv8XOenjJ8+d
UX/ZX/W3F2QIPBxcUW1OKol2J8HFhp5qHMTBspFOI83ms8MPFItJQukXS3EoFyHyLoWbpfutWi8U9myNy3k6vnX85J0z6q8vF19p
yKWbMwxtOPAo5XO1LHtrPeb3QNBu3R565vjpP53R/H8WMAfelaRW3q/0wigdwFIK3mm1w3hEQzO63x1iBlB76oPJolh5uRyfQsEK
qR4TZ5rquT9hjL9oYzx+8coZ6f8+9dfX92rciwd9UhlJlyCxAglyJFH2IOH7Y+E+x3D0xEEnq7V2I/GdXw7lCR0RaatOHwVBFqgN
AAx5mwILjoQ7LegytaMWJJLY4pXqt63uSoxAVQLSDQKwYIbASZYc089UynSV7PGrl86ov15gAKiNpcmCMhACBZ1174nHy8+H8GPl
Pmfw6twZkSQjqkpIUWdsJbLyJowHCFuFMYovkFXpVrnxYnUpGVtTm/s0aKzAjADpUQrFLVqCewm8a1E20wJ5LHUFfespLrOSVbkb
lWx0O7py4jaKtqRrYkdRBJWzXEPZ9e55+lQIpdWWljXrTy+ONL/99dH6ExDPtGZZS26Zbo0+PpGCgKgUtw5yvWqRGMjA7gTBogIC
E7giTXMv935/6T43cvLGQcaVVAwd00i67H+IRbA2K+/IncrPojhbmH8o8LsH+3bL9nq2OOHkKe+7mS/nV+uV+/X9y/OzGRNOZv3t
bD3fbNfL+eV/zb4K8/7r2+zrbTUjFHDZry9nL89ex9nf9AF/my3+Nfuynl8sbher5eym32zm69vfHFWeUuZSKrskEhiGgJHEq5Gm
FFjp5FOIiQ3TN2SvZXEkSgDKsUmZ7gjrgrImQ51CTX9LImUdp9uTj19/cEar7+RL/7OdC7E3pN6pBmx/iDEmmnKfIrPIpAdv1Zo1
zXPaGMxOs+eg7FsZrDR+wCMzZcIvnnCdXfvUVk51zFC/XS8245ATSouoSWQSQkcpgUxNIqYU7FERSfBWGVVFi/TUFAZmaj52Ucqa
Cj76t80Rp5AuBpomcP0m93ImkYN05bfz9brfOGtJCZRuUilAi30BwlCm99CxGNbtw2Fvz5yRvfqCcuaM4pKHJN0iMZVcSstRjjZU
wrVAMfqngySbnjBa7aw/2nzp4RpoGZYDHGP0u05kybywOd28kekeYdr8vJeqfW/qtv9DCpc+mY5KyLLrgmmJSEm8PCkRGtWj+A/X
g1J6WUdvriLB+2Zsjc5W9Y8vdqdzuJBAfgoEndFeU/v5XacDaT/fbseS0SBlJqeqGzO+uNqyUaGmjFN86ZLFpvG5R5tlfXk1UWVv
jaG0UMgsi5nFNXHId0t3E8wgKpCmUdvJwbEz6m8WVmawu/7YJZO9NIRA9Th6I7EWYH+7uvtL/j+FzCeHr5yRVh321ztTzMiXxhwJ
xjkE3X62PFZXHqKgYd0erHjy9NQZLa7ma2u5Jr5swxEEe20qRI0P3+aHBZm7hfs87PmBM1qMdcByzxqCNmlXHkOEF6xIk53uDeyL
PiIFIv+J0ib5vrBCJ4gujDvWx9ATLm7UrdKYk6nQpY+q4CaIlSdv9eWhM1oI+fZXWxuz5C3iL7OrI2D0TNGj6LyWuA3JW5o3KMWy
Yoeuk48drQSYtEoYPTtxpsTHcvxySjt6uhqCL0Rgp3fz1hkt0MposYCnyvyBJPRFhT29WH+qLRvW7XMNrwT3oDm2dbSn9N8x7SFK
pdg9UzCdA5G+TN8K4bKE1yZEJMQxVHvV9H/XAkjUfvpkbd+MIhIjCpTc67umWFbKnYiSjnH6Ql6LE6HV+o/+mzAoxWLsKdZjOLjW
oWZSLpJbGsR0YXSjMhhHHzw64zagybIVtFrarJrIxCMKYkDlWh+sSCAzrUp+8uR+3kgWofmXns70mrJFwpsyy7piTGFrGi88aAO/
t3KfiznV7UOyC1sT+xKtKy5Jg3M9dLbKXf+T8zOs2+dJH/RSHwZF82He7xKznbE2scPhJPFYdP0gzpr8CZ4o0ShZvA47JGxMfJBa
NdngURblN0XWUEpsuR78WVngzLye6RrD18cnzuiGnAqTPir6QbJV0ui6C+loykrHoDsNiNmGWLXRuhZoV/GexqJ63Iu2rauW0fZi
DbxaGhpo+ooAramNvDk4ckb953HqXGzJClGkN4Jwz7yYjkAtZYxB+JLe1pZ6XH/X4yafLzOohTE0dFY8olk+CB4Vgh2WTpEvG/kk
kmR+ej8nzkj49walqe1UJHSihcIpykk1/cOMObL3FhpLkehc18piW2dT40mR7bCjFpQmU4RF3FmuFIGDjn1MIoQ3h9oBtNhc9Iu1
5QclmJ4aF+kmKbdIiJtc1oMg4G7dHuz5RhbJaI4chEaqqB1CEWOVi0AO+bAGfUgVQaYiqRKPjKX04hjrTKE+Vi/VYabMbFZSG2DT
QTPZWB9xtLZPTcT0wLk3cs2NPi2uF1++LJYEJ5iXwIQ0acNxZBvldwVviOoSdkulOvy7S7GJTeg/oXucSQFUm1DxASzSO+o6hCaL
za8rsu7TEwTeyB8z6r9s+xlSvKtEJMlX2VA5BIcKBmmMhkijuO7n+Pu9pfvczWsdA7QatIZemEBUNWSJvRSVTbaro3n6keYj5nNU
hM6GCuGWUDWL9K+h/kgS6234yO5iIpbVYt00zIuzJ6H7m1NJqmiXy3oyv6lmb+arL9fzv93u2prpY5cxLjbOJTA7hKo7w/UPqi12
C/c5EDkxRvJVt1fYiWTDD6gNK96Ar4FREGFD95RsqE5HPGsDSnRK9R3TiiWKlARunXiEIQHy36MFkTwV1dRG003RWW+sPMMy3ZP/
5vR3ZzRgm29We5Gto37M2FntxZDLp9rLY+IpeKo8mGY3hZCpBsga19HRzYHGrWqhs52bQQGb3KOCI8uswslQwpuzpw6iD2j2uF9+
toTn8/47QX4GCSLLQa5dtgEGNf1AdS52RzI0upCW8UKCpbI40rRlVGk50IfCYDXKgWR5kvwmOj7CtET//sxB4zxAcfO3sYSLsZRC
QYa2W1Phnm5kX8KfzK6t24NV/nFw7ox6K8bWoQpGJ2tgHvRDlrNKWiExZ9E7OiKH8XNEvhITEobxes1dA6uOw7KY2EYrDbcS64xf
RE3p1Oufvj52p6/futPVjbnev17Pr/qLbzMCHf/vcHWzWfeXc4t4/NeD0MbidvY3/c2//eZs3kiMQh9lqP5nxplMJN2MSBntxy2z
+WRsdp2RNfMjrbPfR6YOlqGPvlCJ3IwKINhQOkErOvPqaGpz8j3eHzijP9ijjtQKRJroLSGog5JZ6ijqT/5B8vFu4R73d3bw1hn1
28uFjR1djAZZ+0ezjHbAA6Xp5A3D4DIxkM+VZVGI6FB3QrNfTsxj2RUGSz9QHE0pWLObzkqHZQF0e6t0nNSCZ09PnBEBK1QQmY4q
ko6iZsGLp6hPJZ5Q0hjEz1T0Ch5gJ6gNknuBS55/xJhaVEFikpnFdQLjSinnrJvpcr8zme2z08fayfrj3nylvwhf1a1sATFNP4Yf
kABSyFIJoKnM2EWckqob81iJChFrh2HuDjXwgq3J+iqk1YjW1t4CGLnOOJCTu3/+xhktllf9lxVDQxh1RAtHyxS4oRUTP0wH2eGV
FhIHhK0YkJZ2MVqGIUV6q2lfoVuTIi6xmZwlIiaPAGAdA8swgt1fFK2dPT9zRlacMba5mNYcfnKm3/6xkAK7C4xSiVEsL8Nt1kBD
oSQybd7fdxtt1T68/0LsBfULbfPF/HpuBeKRmiDKdggCYdzoTYp/niWxW7fPE1+JjSAmd6zujRrwzA9w+AcdhbUMhNFLdg96LYZV
ez3vqTNaEAKcvZqvlnMz5gzr7Ky5IzPUU1rJYrhjXckPoHu3cq+HvnPQ02vd5fXXoVkZmSeFlMz5YzKV9IX1c5Y4TqbqZDfo4mkJ
3lMDKLQrZTvOn2NYqmfcwxCQlTtsHd+kqqZZ7ViSC/VDuH1JUgxVVjG1qSV5S8u6fCnKkGSpHjRq31u6z/vLEBnJEF0PJRYMJGXe
D6lwuaRET8gnPuyx/LFwn8e90aOgjVAi9zw3YTomFH5NPc0w+wDzQYAbl8qmlwSGaP/cXDGs2+fZZ0+c0SC528vBt2wshWTglJi7
AGBJuLVSVA/w+o+l+zz1XOoM6lez89XN8L5vdL0Xiy9Mjmqqlog+48sbZq3CUHQPPBg+c7dun0e/1cs+kcqwV93TFDw5kSkQEq6o
wWuZCpOZqiUXi0Kr/MDJ/LFwr/2J26GtjqO/seYqWpUjUX+gr6fLSu6YXJnhedGiX0ObUyebRM0WY0aEm+3PixQAkzBiTe5PKl9u
dj0M0ZmSundHzuh69bX/fH8EnPxxSa1upR3dR6EFxk53nTV3+o6RK0AGrPpY80EfobA7Xe1NCMGK5Km46BhSRyMBWUBB6yZaezj9
OpP70r1B2tcwNhxEWlN+vBsBKrOon+kp1pJDqkR7Dp6pQX4so2+oEazh6cjoQh2DWNzXNKeRpQrUWkSbm4XPE6c9h7P30svQH/PL
OWVvOv7iiYMEv+s5lhrMDLCmrb9JrlAvXFOD1uz6LBodCq2zjPySg2UtBB0d77mmOEEqXJuXoyr9zuyaND3S4uz9Bwc9vf2j3yyW
C/RWEsSLeCEFx5vZzjR+6NqG0VmCuZgHY55ALDTVXFYrJTdWTfDtAgx9aHHzmCdCaII2C/Ldkzv5/dAZzb9dfJpfX9sE/GI+oqGA
xLBlRipgDobIofVuGJvaFOhovblJViaN9iMIzUrR6zPGX2IkHaUYK+MrRvtegekNSaKgb6Rsh+H899jaGn1BR8XaXb2XKe2YydOl
B/GJ+0v3kOrzwwNntF1/HipqD/sFAwTvQaREmTrjW1vZcrIbkVqpP2X2hmV7PfuJgw4/9dakWOHAkLegeoVIC98eMCQr7yOV3bp9
nvT8tTNaXclOCwlVtO3wqJBwm5phJG2THvRd/Vi5z8Ne6DihT/1i7ChBGZeuonR9TMcR8cqMaqXoTEJADFz8R2HtrpSb/iMGpovl
mJ7fIa/MUmyHXAHlwdToCst0aBID7xNcdv73I2fU/3uxi9MyNSfZ3IURh0extMQ4M4CYjo3E4NhEudkuksg0AsYZMWzTpppILjsC
INols0wpemMqjXxamcXJzRy9ckarz/Prfgtuwh+wgjb9VWqzvDm9MT/4JoO7hfvcxtGxMxKD85UOw8vLv7EvkOjuKkWabPP82QCV
O+n+bO/7i/d59PEbd/7qzJ0vblbrR68Y57KnXdffll3PDCKorYCUdqDUyYQ0NiHr5+PZrdtni69PnNFKLhx1InyZQXbU0Mr5y9wE
Y/3ah3Uiw7J9HnQu6YMEHhaX/aWpmvPVxx6BpKqwYracCT9fGVOawIAGPf5B2daPlfs8/K3eENrq/ocBzi3F+i2x/vH6abJoGdbF
mEpaMjOZMgyPTG+qaKqSWyoRYdLYriaVgmP4vwnDFOWKVGyxfnZdxaTbfy4YZcTc+2+4TQS3ahLfdRPGQan0idE5ogtgbCypLVpX
W0bDD5hCxxPMfQwMawg6J8ZJ13T10baCipCV5VtI5DVLezTa7PSW3jmj7df+ekuPvs25x41jFkwbrY25tPFhi/6wbJ/L+CDVCPXL
70MhC41lVoeyq8kKkckOuMAd32uQHaa1ylZabwFPj8puqJsZ520/ivS8VRYCs4BYw6AbvjKCr++ZBEpvnx84o6shICYwKx3DtHJw
ibcxxlY5wtCpwZXkayoqijQYN9x566WvDXrkXaky00+JLOJ60GxTU15OczBx7cmtHJ06o88M3J9bqSsdaySt/JAMaLyFk/lgn+/H
Vn9aucdVvD1+6YyGSSVnG74SSO7dUktebzfX3xbLqx9AgGaUUNugZ8qNs8BYQRu3/oH3c7dwn62cnDmj5e2X+cXiXwvtR0s3s/76
enXRs73NatbPbrWlaxSmfY/WbwyvaykzpTNqDMLTjhx12i3VEPm+9vhp7T6bO/3dGa23Q26A0iLdMaB6TFY1vqFpUBzTdi3N7AxX
jgznHEuCxK4tK5hyl8x4F/kYlQWodxU/DHXp+JoinBQ5mNOI+u2ZmBa6f3MADb6UgY5BUp32FQCFMegkHxhAz1dH0N7fVD+qfvjm
HEpBmkgrPJeWUipSPlVuLaVgtUgJhzcxTa2l1mSajT88dkbfP853SEOXwIyWyuu0BnTT2pQCq8GTpLeBDHZk3JinQniYN8bwSeEy
Un1MZ3KgcuET5GCo2SouU+GEyxDJdsfpwVTvDs4d9GKlyz6bz2e/vpMjwty/w8Xm23B8v5HMiA3wnclwgR14vn+EqriHyYxh3R4s
9O7piTOaL+fft3P7tjRdi05V9++StS3DVFR8hPIAht5buc8jnz920GPK5m4/zd4t1leL+4FBvjqD4l+6Kijs8qZy/RDSvg+7dgv3
efjJsTNazDdLxnA0fEIY6o2H5KdMkowHMCObhXFkhCmeZMLgMJMEzzARzq4JyTFrmKHbzDqySaVNGb9wpmGkW83EdIZpTeex3r0V
H0D9cttvtkMIo7OvbaK30oohKOT0DxuUhmV7vP/7V8+ckfTXYnCsnm03WxulX+E98c0RtRQ5SVvGTKSYHn5zybBsj4f+/vTYGc1v
cPt9y8hUpjYwAYcKbKZf60gfKuwfC/d42IeDZw4aAnTDVH7ncseQsgrfYuw+yrQIWyFioO6occxITYkipLbZDeXByga6ViNfkka3
G/MIKmZq5+GCSb0yEB2DM3W9Hw5O3eHrJ3dzui29PWS198Pd+hDhbtJ10lARi+cjF0XEqJE+qIcKpkg/dyGTWjV8ZRRfPsfX4OU8
KIxHkb4m+lqH+trCd3VZNi/+RXrqw/FjZzQOabLivsqa5xBViooLbmOLft6hEmksmszJo9NOIB1SrBV62IcnR8Qog90gs5oqm6DP
EvSaPs73T53R4uZj//GPufUkN6ar7qajenxaRhcKlOj+aBOt6avwgQZL+p+ZQ8GgiruCGnnZfO1Fzs3uGxVrOr1yJo40tZf/BTVG
4aRDcwAA
"""

_META_IMPORTS = {
    "world_imports_2021_usd_thousand": 293497128.020043,
    "world_exports_to_russia_2023_usd_thousand": 258924551.380259
}


@st.cache_data
def load_imports_data():
    raw = gzip.decompress(base64.b64decode(_TRADE_IMPORTS_DATA_B64))
    df = pd.read_csv(io.StringIO(raw.decode("utf-8")))
    return df, _META_IMPORTS


df_imp, meta_imp = load_imports_data()

WLD_IMP_OWN = meta_imp["world_imports_2021_usd_thousand"] / 1000  # Russia's own 2021 imports, US$M
WLD_EXP_TO_RUS = meta_imp["world_exports_to_russia_2023_usd_thousand"] / 1000  # 2023 mirror, US$M

df_imp["Value2021_m"] = df_imp["Value2021"] / 1000
df_imp["Value2023_m"] = df_imp["Value2023"] / 1000
df_imp["abs_change_m"] = df_imp["abs_change"] / 1000

# --------------------------------------------------------------------------
# EU <-> Former USSR data (own-reported, first-party data on both sides for
# 11 of the 12 FSU countries; Russia is partner-reported "mirror" data since
# Russia itself stopped publishing detailed customs data after 2022 - see the
# EU/FSU methodology note in that tab for exact source queries)
# --------------------------------------------------------------------------
_EU_FSU_DATA_B64 = """
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
"""


@st.cache_data
def load_eu_fsu_data():
    raw = gzip.decompress(base64.b64decode(_EU_FSU_DATA_B64))
    return pd.read_csv(io.StringIO(raw.decode("utf-8")))


eu_fsu_df = load_eu_fsu_data()
EU_COUNTRIES = sorted(eu_fsu_df["eu_country"].unique().tolist())
FSU_COUNTRIES = sorted(eu_fsu_df["fsu_country"].unique().tolist())

# One shared ceiling for every $-valued map and bar chart in the EU-FSU tab
# (both aggregation levels, both years, both flow directions), so a given
# dollar amount always renders at the same color intensity / bar length no
# matter which specific chart it appears on - never re-normalized per chart.
EU_FSU_GLOBAL_MAX_M = max(
    eu_fsu_df.groupby(["year", "flow", "fsu_country"])["value_th"].sum().max(),
    eu_fsu_df.groupby(["year", "flow", "eu_country"])["value_th"].sum().max(),
) / 1000

# --------------------------------------------------------------------------
# Global styling
# --------------------------------------------------------------------------
st.markdown(
    f"""
    <style>
    /* Force the dark palette this app is designed for, regardless of the
       user's OS/browser light-mode setting - otherwise Streamlit can render
       a light page behind this app's light text and make it unreadable. This
       is a backup for the .streamlit/config.toml written at launch. */
    html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{
        background-color: {SURFACE} !important;
        color: {INK_PRIMARY} !important;
    }}
    [data-testid="stSidebar"] {{ background-color: {PAGE_PLANE} !important; }}
    p, span, div, label, li, td, th {{ color: {INK_PRIMARY}; }}
    .block-container {{ padding-top: 1.6rem; }}
    .kpi-row {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 0.5rem; }}
    .kpi-tile {{
        flex: 1 1 200px;
        background: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 10px;
        padding: 14px 18px;
    }}
    .kpi-label {{
        font-size: 0.78rem;
        color: {INK_MUTED};
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 4px;
    }}
    .kpi-value {{
        font-size: 1.65rem;
        font-weight: 600;
        color: {INK_PRIMARY};
        line-height: 1.15;
    }}
    .kpi-delta-up {{ color: {GOOD_TEXT}; font-size: 0.9rem; font-weight: 600; }}
    .kpi-delta-down {{ color: {BAD_TEXT}; font-size: 0.9rem; font-weight: 600; }}
    .kpi-sub {{ color: {INK_SECONDARY}; font-size: 0.82rem; margin-top: 2px; }}
    .caveat {{
        background: {PAGE_PLANE};
        border-left: 3px solid {ACCENT_BLUE};
        padding: 10px 14px;
        border-radius: 4px;
        font-size: 0.88rem;
        color: {INK_SECONDARY};
        margin-bottom: 1rem;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Where Russia's exports went: 2021 vs. 2023")
st.markdown(
    """
    <div class="caveat">
    <b>Reading this dashboard:</b> the 2021 map is Russia's own export reporting
    (last full year before it stopped publishing customs data). The 2023 map is
    <i>mirror data</i> &mdash; what each partner country itself reported importing
    from Russia, since Russia no longer reports. The two are collected differently,
    so treat the comparison as directional, not precise to the dollar. See the
    "Methodology" tab for the exact source queries.
    </div>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# KPI row
# --------------------------------------------------------------------------
world_pct_change = (WLD_IMP - WLD_EXP) / WLD_EXP * 100
both = df[df["status"] == "Present in both years"]
gainers = int((both["abs_change"] > 0).sum())
losers = int((both["abs_change"] < 0).sum())
dropped = int((df["status"] == "Only in 2021 (no 2023 mirror data)").sum())
top_gainer = both.sort_values("abs_change", ascending=False).iloc[0]
top_loser = both.sort_values("abs_change", ascending=True).iloc[0]

both_imp = df_imp[df_imp["status"] == "Present in both years"]

# One shared color/size ceiling for the change map + top-movers bar chart,
# covering BOTH the exports view and the imports view (same principle as the
# EU-FSU tab: a given dollar change always looks the same regardless of
# which flow direction is currently selected).
CHANGE_GLOBAL_VMAX_M = max(
    both["abs_change_m"].abs().max(),
    both_imp["abs_change_m"].abs().max(),
)

delta_class = "kpi-delta-down" if world_pct_change < 0 else "kpi-delta-up"
delta_sign = "" if world_pct_change < 0 else "+"

st.markdown(
    f"""
    <div class="kpi-row">
      <div class="kpi-tile">
        <div class="kpi-label">World total, 2021 exports</div>
        <div class="kpi-value">${WLD_EXP/1000:,.1f}B</div>
        <div class="kpi-sub">Russia-reported</div>
      </div>
      <div class="kpi-tile">
        <div class="kpi-label">World total, 2023 imports from Russia</div>
        <div class="kpi-value">${WLD_IMP/1000:,.1f}B</div>
        <div class="kpi-sub">Partner-reported (mirror data)</div>
      </div>
      <div class="kpi-tile">
        <div class="kpi-label">Change, world total</div>
        <div class="kpi-value"><span class="{delta_class}">{delta_sign}{world_pct_change:,.1f}%</span></div>
        <div class="kpi-sub">${(WLD_IMP-WLD_EXP)/1000:,.1f}B</div>
      </div>
      <div class="kpi-tile">
        <div class="kpi-label">Countries: exports up / down</div>
        <div class="kpi-value">{gainers} <span class="kpi-sub" style="font-size:1rem;">up</span> &nbsp;/&nbsp; {losers} <span class="kpi-sub" style="font-size:1rem;">down</span></div>
        <div class="kpi-sub">{dropped} present in 2021 with no 2023 mirror record</div>
      </div>
      <div class="kpi-tile">
        <div class="kpi-label">Biggest export increase</div>
        <div class="kpi-value">{top_gainer['Country']}</div>
        <div class="kpi-sub"><span class="kpi-delta-up">+${top_gainer['abs_change_m']:,.0f}M</span></div>
      </div>
      <div class="kpi-tile">
        <div class="kpi-label">Biggest export decrease</div>
        <div class="kpi-value">{top_loser['Country']}</div>
        <div class="kpi-sub"><span class="kpi-delta-down">-${abs(top_loser['abs_change_m']):,.0f}M</span></div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")

# --------------------------------------------------------------------------
# Sidebar controls
# --------------------------------------------------------------------------
st.sidebar.header("Controls")
metric_choice = st.sidebar.radio(
    "Map metric (2021 / 2023 views)",
    ["Trade value (US$)", "Share of world total (%)"],
    index=0,
)
log_scale = st.sidebar.checkbox(
    "Log-scale the value maps",
    value=True,
    help="China, the Netherlands and Germany dwarf most countries in raw dollars; "
    "log scale keeps mid-size partners visible.",
)
highlight_country = st.sidebar.selectbox(
    "Highlight a country in the table",
    ["(none)"] + sorted(df["Country"].unique().tolist()),
)
st.sidebar.caption(
    "Data: UN Comtrade via World Bank WITS. 2023 column is mirror (partner-reported) "
    "data because Russia stopped reporting after 2022."
)

# --------------------------------------------------------------------------
# Map builders
# --------------------------------------------------------------------------
NICE_TICKS_USD_M = [1, 10, 100, 1_000, 10_000, 70_000]  # US$ million


def fmt_usd_m(v):
    sign = "-" if v < 0 else ""
    v = abs(v)
    if v >= 1000:
        return f"{sign}${v/1000:,.0f}B"
    return f"{sign}${v:,.0f}M"


def build_value_maps(data, use_share, use_log):
    if use_share:
        col21, col23 = "Share2021", "Share2023"
        z21_raw = data[col21] * 100
        z23_raw = data[col23] * 100
        cbar_title = "Share of<br>world total (%)"
        vmax = max(z21_raw.max(), z23_raw.max())
        vmin = 0
        tickvals_raw = None
    else:
        col21, col23 = "Value2021_m", "Value2023_m"
        z21_raw = data[col21]
        z23_raw = data[col23]
        cbar_title = "Trade value"
        vmax = max(z21_raw.max(), z23_raw.max())
        vmin = 0
        tickvals_raw = [t for t in NICE_TICKS_USD_M if t <= vmax * 1.05]

    if use_log:
        z21 = np.log10(z21_raw + 1)
        z23 = np.log10(z23_raw + 1)
        zmax = np.log10(vmax + 1)
        zmin = 0
        if tickvals_raw:
            tickvals = [np.log10(t + 1) for t in tickvals_raw]
            ticktext = [fmt_usd_m(t) for t in tickvals_raw]
        else:
            tickvals = [np.log10(t + 1) for t in [0, 5, 10, 25, 50, vmax]]
            ticktext = [f"{t:,.0f}%" for t in [0, 5, 10, 25, 50, vmax]]
    else:
        z21, z23 = z21_raw, z23_raw
        zmin, zmax = vmin, vmax
        if tickvals_raw:
            tickvals, ticktext = tickvals_raw, [fmt_usd_m(t) for t in tickvals_raw]
        else:
            tickvals = None
            ticktext = None

    def trace(z, raw, year, present_mask):
        hover_val = (
            [f"{v:.2f}%" for v in raw] if use_share else [fmt_usd_m(v) for v in raw]
        )
        z_masked = z.where(present_mask)  # NaN out "not present this year" so it reads as no-data, not near-zero
        return go.Choropleth(
            locations=data["iso3"],
            z=z_masked,
            zmin=zmin,
            zmax=zmax,
            customdata=np.stack([data["Country"], hover_val, data["status"]], axis=-1),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                + year
                + ": %{customdata[1]}<br>%{customdata[2]}<extra></extra>"
            ),
            colorscale=SEQ_BLUE,
            marker_line_color=GRIDLINE,
            marker_line_width=0.4,
            colorbar=dict(
                title=cbar_title,
                tickvals=tickvals,
                ticktext=ticktext,
                len=0.75,
                thickness=14,
                outlinewidth=0,
            ),
        )

    present21 = data["Value2021"] > 0
    present23 = data["Value2023"] > 0
    fig21 = go.Figure(trace(z21, z21_raw, "2021", present21))
    fig23 = go.Figure(trace(z23, z23_raw, "2023", present23))
    for fig, year_label in [(fig21, "Russia's exports, 2021"), (fig23, "Imports from Russia, 2023")]:
        fig.update_geos(
            showframe=False,
            showcoastlines=False,
            projection_type="natural earth",
            landcolor=LANDCOLOR,
            bgcolor=SURFACE,
        )
        fig.update_layout(
            title=dict(text=year_label, font=dict(size=15, color=INK_PRIMARY)),
            margin=dict(l=0, r=0, t=36, b=0),
            paper_bgcolor=SURFACE,
            height=420,
            font=dict(color=INK_SECONDARY),
        )
    return fig21, fig23


def build_change_map(data, flow_label="export", vmax_override=None):
    # Only show countries with a genuine 2021-vs-2023 comparison. Countries
    # that dropped out of the 2023 mirror data ("Only in 2021") are excluded
    # too, not just newly-appearing ones - otherwise a reporting gap (no
    # partner reported trade with this country in 2023) would render as if
    # it were a real ~100% collapse, which is misleading.
    plot_df = data[data["status"] == "Present in both years"].copy()
    vmax = float(vmax_override) if vmax_override is not None else plot_df["abs_change_m"].abs().max()
    flow_cap = flow_label.capitalize()
    fig = go.Figure(
        go.Choropleth(
            locations=plot_df["iso3"],
            z=plot_df["abs_change_m"],
            zmin=-vmax,
            zmax=vmax,
            customdata=np.stack(
                [
                    plot_df["Country"],
                    plot_df["abs_change_m"].apply(lambda v: f"{'+' if v>=0 else ''}{fmt_usd_m(v)}"),
                    plot_df["pct_change"].apply(
                        lambda v: f"{v:+.0f}%" if pd.notna(v) else "n/a (baseline was $0)"
                    ),
                    plot_df["status"],
                ],
                axis=-1,
            ),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>" + flow_cap + " change: %{customdata[1]} "
                "(%{customdata[2]})<br>%{customdata[3]}<extra></extra>"
            ),
            colorscale=DIV_BLUE_RED,
            zmid=0,
            marker_line_color=GRIDLINE,
            marker_line_width=0.4,
            colorbar=dict(
                title=f"{flow_cap} change<br>(US$ M)",
                len=0.75,
                thickness=14,
                outlinewidth=0,
            ),
        )
    )
    fig.update_geos(
        showframe=False,
        showcoastlines=False,
        projection_type="natural earth",
        landcolor=LANDCOLOR,
        bgcolor=SURFACE,
    )
    fig.update_layout(
        title=dict(
            text=f"Change in Russia's {flow_label}s, 2021 -> 2023",
            font=dict(size=15, color=INK_PRIMARY),
        ),
        margin=dict(l=0, r=0, t=36, b=0),
        paper_bgcolor=SURFACE,
        height=480,
        font=dict(color=INK_SECONDARY),
    )
    return fig


# --------------------------------------------------------------------------
# EU <-> Former USSR map builder (shared by the aggregate FSU maps and the
# clickable EU maps - the only difference is which set of countries is
# colored, and whether a "selected" country gets an accent outline)
# --------------------------------------------------------------------------
def build_region_choropleth(iso3_list, values_raw, hover_names, cbar_title, use_log, highlight_iso3=None, height=420, vmax_override=None):
    vmax = float(vmax_override) if vmax_override is not None else max(float(values_raw.max()), 1.0)
    vmax = max(vmax, 1.0)
    tickvals_raw = [t for t in NICE_TICKS_USD_M if t <= vmax * 1.1]
    if not tickvals_raw:
        tickvals_raw = [vmax]

    if use_log:
        z = np.log10(values_raw + 1)
        zmin, zmax = 0, np.log10(vmax + 1)
        tickvals = [np.log10(t + 1) for t in tickvals_raw]
    else:
        z = values_raw
        zmin, zmax = 0, vmax
        tickvals = tickvals_raw
    ticktext = [fmt_usd_m(t) for t in tickvals_raw]

    iso3_l = list(iso3_list)
    line_colors = [GRIDLINE] * len(iso3_l)
    line_widths = [0.5] * len(iso3_l)
    if highlight_iso3:
        for i, code in enumerate(iso3_l):
            if code == highlight_iso3:
                line_colors[i] = ACCENT_ORANGE
                line_widths[i] = 3.5

    hover_value_text = [fmt_usd_m(v) for v in values_raw]
    fig = go.Figure(
        go.Choropleth(
            locations=iso3_l,
            z=z,
            zmin=zmin,
            zmax=zmax,
            customdata=np.stack([list(hover_names), hover_value_text], axis=-1),
            hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<extra></extra>",
            colorscale=SEQ_BLUE,
            marker_line_color=line_colors,
            marker_line_width=line_widths,
            colorbar=dict(title=cbar_title, tickvals=tickvals, ticktext=ticktext, len=0.8, thickness=14, outlinewidth=0),
        )
    )
    fig.update_geos(
        showframe=False,
        showcoastlines=False,
        projection_type="natural earth",
        landcolor=LANDCOLOR,
        bgcolor=SURFACE,
        fitbounds="locations",
        visible=False,
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor=SURFACE,
        height=height,
        font=dict(color=INK_SECONDARY),
    )
    return fig


def eu_fsu_agg_by_fsu(eu_fsu_df, year, flow):
    """Sum across all 27 EU reporters, one row per FSU country."""
    sub = eu_fsu_df[(eu_fsu_df["year"] == year) & (eu_fsu_df["flow"] == flow)]
    agg = sub.groupby(["fsu_country", "fsu_iso3"], as_index=False)["value_th"].sum()
    agg["value_m"] = agg["value_th"] / 1000
    return agg.sort_values("value_m", ascending=False)


def eu_fsu_agg_by_eu(eu_fsu_df, year, flow):
    """Sum across all 12 FSU partners, one row per EU country."""
    sub = eu_fsu_df[(eu_fsu_df["year"] == year) & (eu_fsu_df["flow"] == flow)]
    agg = sub.groupby(["eu_country", "eu_iso3_map"], as_index=False)["value_th"].sum()
    agg["value_m"] = agg["value_th"] / 1000
    return agg.sort_values("value_m", ascending=False)


def eu_country_breakdown(eu_fsu_df, eu_country, year, flow):
    """For one EU country: its trade with each FSU partner, as % of that
    EU country's total FSU-region trade for this year/flow."""
    sub = eu_fsu_df[
        (eu_fsu_df["eu_country"] == eu_country)
        & (eu_fsu_df["year"] == year)
        & (eu_fsu_df["flow"] == flow)
    ].copy()
    total = sub["value_th"].sum()
    sub["pct"] = sub["value_th"] / total * 100 if total > 0 else 0.0
    sub["value_m"] = sub["value_th"] / 1000
    return sub.sort_values("pct", ascending=False), total / 1000


def build_breakdown_bar(breakdown_df, unit_label):
    d = breakdown_df.sort_values("pct")
    ylabels = d["fsu_country"]
    if "is_mirror" in d.columns:
        ylabels = [
            f"{n} *" if m else n for n, m in zip(d["fsu_country"], d["is_mirror"])
        ]
    fig = go.Figure(
        go.Bar(
            x=d["pct"],
            y=ylabels,
            orientation="h",
            marker_color=ACCENT_BLUE,
            customdata=d["value_m"],
            hovertemplate=f"<b>%{{y}}</b><br>%{{x:.1f}}% of {unit_label}<br>$%{{customdata:,.0f}}M<extra></extra>",
            text=[f"{v:.1f}%" for v in d["pct"]],
            textposition="outside",
            cliponaxis=False,
        )
    )
    fig.update_layout(
        height=340,
        margin=dict(l=10, r=30, t=10, b=10),
        plot_bgcolor=SURFACE,
        paper_bgcolor=SURFACE,
        # Fixed 0-100 range (not auto-scaled to this chart's own max) so a
        # given percentage is always the same bar length on every breakdown
        # chart in the app - never re-normalized to whatever the biggest
        # slice happens to be in one particular country/year.
        xaxis=dict(
            title="% of total", range=[0, 108], gridcolor=GRIDLINE, zerolinecolor=INK_MUTED,
            ticksuffix="%",
        ),
        yaxis=dict(title=""),
        font=dict(color=INK_SECONDARY),
    )
    return fig


def build_ranked_bar(data_2021, data_2023, name_col, flow_label, xmax, height=420, mark_mirror=False):
    """Horizontal grouped bar chart: one bar for 2021, one for 2023, per
    country, sorted so the biggest total (2021+2023) ends up at the top.
    `xmax` is a shared ceiling passed in by the caller (EU_FSU_GLOBAL_MAX_M)
    so a given dollar value is always the same bar length on every ranked
    bar chart in this tab, not re-scaled to this chart's own biggest bar."""
    d21 = data_2021[[name_col, "value_m"]].rename(columns={"value_m": "v2021"})
    d23 = data_2023[[name_col, "value_m"]].rename(columns={"value_m": "v2023"})
    merged = pd.merge(d21, d23, on=name_col, how="outer").fillna(0.0)
    merged["total"] = merged["v2021"] + merged["v2023"]
    merged = merged.sort_values("total")  # ascending: horizontal bars stack biggest-on-top

    if mark_mirror:
        ylabels = [f"{n} *" if n == "Russia" else n for n in merged[name_col]]
    else:
        ylabels = merged[name_col]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=merged["v2021"], y=ylabels, orientation="h", name="2021",
            marker_color=BLUE_STEPS[3],
            hovertemplate="<b>%{y}</b><br>2021: $%{x:,.0f}M<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=merged["v2023"], y=ylabels, orientation="h", name="2023",
            marker_color=BLUE_STEPS[9],
            hovertemplate="<b>%{y}</b><br>2023: $%{x:,.0f}M<extra></extra>",
        )
    )
    fig.update_layout(
        barmode="group",
        height=height,
        margin=dict(l=10, r=10, t=10, b=10),
        plot_bgcolor=SURFACE,
        paper_bgcolor=SURFACE,
        xaxis=dict(
            title=f"EU {flow_label} (US$ million)", range=[0, xmax * 1.03],
            gridcolor=GRIDLINE, zerolinecolor=INK_MUTED,
        ),
        yaxis=dict(title=""),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        font=dict(color=INK_SECONDARY),
    )
    return fig


def _extract_click_point(event):
    """First clicked point dict out of a Streamlit plotly on_select event, or
    None. Defensive against dict-like vs attribute-style event shapes across
    Streamlit versions."""
    if not event:
        return None
    try:
        sel = event["selection"] if "selection" in event else None
    except (TypeError, KeyError):
        sel = getattr(event, "selection", None)
    if sel is None:
        return None
    try:
        points = sel["points"] if "points" in sel else None
    except (TypeError, KeyError):
        points = getattr(sel, "points", None)
    if not points:
        return None
    return points[0]


def _clicked_eu_country(event, eu_fsu_df):
    """Map a click event on one of the EU choropleths back to an EU country
    name, trying the ISO3 'location' field first and falling back to the
    country name we embedded as customdata[0]."""
    pt = _extract_click_point(event)
    if not pt:
        return None
    loc = pt.get("location") if hasattr(pt, "get") else getattr(pt, "location", None)
    if loc:
        m = eu_fsu_df.loc[eu_fsu_df["eu_iso3_map"] == loc, "eu_country"]
        if len(m):
            return m.iloc[0]
    cd = pt.get("customdata") if hasattr(pt, "get") else getattr(pt, "customdata", None)
    if cd is not None and len(cd) > 0:
        name = cd[0]
        if name in EU_COUNTRIES:
            return name
    return None


def _sync_eu_click(eu_fsu_df, map_key, country_key, default_country):
    """Pull in any pending click from the paired map (map_key) into the
    selectbox's session_state (country_key) BEFORE that map/selectbox get
    built this run, so the highlight and breakdown chart never lag a click.

    Streamlit keeps a chart's last selection in session_state forever (it
    doesn't clear just because the script reran without a new click), so we
    track the signature of the last click we already applied and only act
    again when it changes - otherwise a single map click would permanently
    pin the selection and the dropdown fallback could never override it."""
    if country_key not in st.session_state:
        st.session_state[country_key] = default_country
    pt = _extract_click_point(st.session_state.get(map_key))
    if not pt:
        return
    loc = pt.get("location") if hasattr(pt, "get") else getattr(pt, "location", None)
    cd = pt.get("customdata") if hasattr(pt, "get") else getattr(pt, "customdata", None)
    current_sig = loc or (cd[0] if cd is not None and len(cd) > 0 else None)
    if current_sig is None:
        return
    sig_key = f"_{map_key}_last_click_sig"
    if st.session_state.get(sig_key) == current_sig:
        return  # already applied this exact click - let other controls (the dropdown) win now
    st.session_state[sig_key] = current_sig
    clicked = _clicked_eu_country(st.session_state.get(map_key), eu_fsu_df)
    if clicked:
        st.session_state[country_key] = clicked


def render_clickable_map(fig, map_key):
    """Render a choropleth with click-to-select if this Streamlit version
    supports it (on_select landed in 1.35+); otherwise fall back to a plain,
    non-interactive map so the tab still works - the dropdown selector next
    to it always works regardless, so nothing is lost, just the shortcut."""
    try:
        st.plotly_chart(
            fig,
            use_container_width=True,
            on_select="rerun",
            selection_mode="points",
            key=map_key,
            config={"displayModeBar": False},
        )
    except TypeError:
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.caption("(Click-to-select needs a newer Streamlit - use the dropdown below instead.)")


# --------------------------------------------------------------------------
# Tabs
# --------------------------------------------------------------------------
tab_maps, tab_change, tab_movers, tab_table, tab_eufsu, tab_method = st.tabs(
    ["2021 vs 2023 maps", "Change map", "Top movers", "Data table", "EU vs Former USSR", "Methodology"]
)

use_share = metric_choice.startswith("Share")

with tab_maps:
    st.caption(
        "Same color scale on both maps (log-scaled by default) so the two years "
        "are visually comparable. Countries not present in a given year are left uncolored."
    )
    fig21, fig23 = build_value_maps(df, use_share, log_scale)
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(fig21, use_container_width=True, config={"displayModeBar": False})
    with c2:
        st.plotly_chart(fig23, use_container_width=True, config={"displayModeBar": False})

CHANGE_FLOW_OPTIONS = ["Russia's exports", "Russia's imports"]

with tab_change:
    change_flow_label = st.radio(
        "Trade direction", CHANGE_FLOW_OPTIONS, index=0, horizontal=True, key="change_flow_label",
    )
    if change_flow_label == "Russia's exports":
        change_flow, change_data = "export", df
        change_source_note = (
            "each country's 2021 figure is Russia's own reported exports to it, and its 2023 "
            "figure is that country's own reported imports from Russia (mirror data)."
        )
    else:
        change_flow, change_data = "import", df_imp
        change_source_note = (
            "each country's 2021 figure is Russia's own reported imports from it, and its 2023 "
            "figure is that country's own reported exports to Russia (mirror data)."
        )
    st.caption(
        f"This is about Russia's {change_flow}s specifically (not "
        f"{'imports' if change_flow == 'export' else 'exports'}, not total trade): "
        f"{change_source_note} Blue = {change_flow}s grew from 2021 to 2023, red = shrank. Gray "
        "= little or no change. This map only shows countries with a genuine reading in both "
        "years. Countries with no 2021 record (new in 2023) and countries that dropped out of "
        "the 2023 mirror data entirely are both excluded - a missing 2023 mirror report doesn't "
        "mean trade actually fell to zero, it usually just means no partner country reported "
        "trade with it that year, so showing it as a ~100% drop would be misleading. See the "
        "Top movers tab and the data table for those countries' 2021 values. "
        "Color scale is fixed across both exports and imports views, so a given dollar change "
        "always looks the same regardless of which one is selected."
    )
    st.plotly_chart(
        build_change_map(change_data, flow_label=change_flow, vmax_override=CHANGE_GLOBAL_VMAX_M),
        use_container_width=True, config={"displayModeBar": False},
    )

with tab_movers:
    movers_flow_label = st.radio(
        "Trade direction", CHANGE_FLOW_OPTIONS, index=0, horizontal=True, key="movers_flow_label",
    )
    if movers_flow_label == "Russia's exports":
        movers_flow, movers_data, movers_both = "export", df, both
        movers_source_note = (
            "2021 = Russia's own reported exports. 2023 = partner countries' own reported "
            "imports from Russia (mirror data, since Russia stopped reporting)."
        )
        movers_dropped_note = (
            "These had recorded Russian exports in 2021 but no partner-reported import record in 2023 "
            "(includes Belarus, Iran, and other countries that may simply not report detailed mirror data "
            "to Comtrade, not necessarily a trade stoppage)."
        )
    else:
        movers_flow, movers_data, movers_both = "import", df_imp, both_imp
        movers_source_note = (
            "2021 = Russia's own reported imports. 2023 = partner countries' own reported "
            "exports to Russia (mirror data, since Russia stopped reporting)."
        )
        movers_dropped_note = (
            "These had recorded Russian imports in 2021 but no partner-reported export record in "
            "2023. This side has a much bigger 2023 reporting gap than the exports side (90 vs. "
            "~20 countries) - see Methodology."
        )
    st.subheader(f"Top 15 increases and decreases in Russia's {movers_flow}s, 2021 -> 2023 (absolute change)")
    st.caption(
        f"{movers_source_note} Same {movers_flow} flow, two different reporting sources - not "
        f"{'import' if movers_flow == 'export' else 'export'} figures and not total trade. Bar "
        "scale is fixed across both exports and imports views, so a given dollar change is "
        "always the same bar length regardless of which one is selected."
    )
    movers = movers_both.reindex(movers_both["abs_change"].abs().sort_values(ascending=False).index).head(15)
    movers = movers.sort_values("abs_change")
    colors = [BAD_TEXT if v < 0 else ACCENT_BLUE for v in movers["abs_change_m"]]
    fig = go.Figure(
        go.Bar(
            x=movers["abs_change_m"],
            y=movers["Country"],
            orientation="h",
            marker_color=colors,
            hovertemplate="<b>%{y}</b><br>" + movers_flow.capitalize() + " change: %{x:+,.0f} US$M<extra></extra>",
        )
    )
    fig.update_layout(
        height=520,
        margin=dict(l=10, r=10, t=10, b=10),
        plot_bgcolor=SURFACE,
        paper_bgcolor=SURFACE,
        xaxis=dict(
            title=f"{movers_flow.capitalize()} change, 2021 -> 2023 (US$ million)",
            range=[-CHANGE_GLOBAL_VMAX_M * 1.05, CHANGE_GLOBAL_VMAX_M * 1.05],
            gridcolor=GRIDLINE, zerolinecolor=INK_MUTED,
        ),
        yaxis=dict(title=""),
        font=dict(color=INK_SECONDARY),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.subheader(f"Countries that dropped out of the 2023 mirror {movers_flow} data entirely")
    st.caption(movers_dropped_note)
    dropped_df = movers_data[movers_data["status"] == "Only in 2021 (no 2023 mirror data)"].sort_values(
        "Value2021", ascending=False
    )
    st.dataframe(
        dropped_df[["Country", "Value2021_m", "Share2021"]].rename(
            columns={"Value2021_m": f"2021 {movers_flow} value (US$M)", "Share2021": "2021 share of world total"}
        ).style.format({f"2021 {movers_flow} value (US$M)": "{:,.0f}", "2021 share of world total": "{:.2%}"}),
        use_container_width=True,
        hide_index=True,
    )

with tab_table:
    st.subheader("Full country-by-country data")
    status_filter = st.multiselect(
        "Filter by status", sorted(df["status"].unique().tolist()), default=[]
    )
    show_df = df.copy()
    if status_filter:
        show_df = show_df[show_df["status"].isin(status_filter)]
    if highlight_country != "(none)":
        show_df = pd.concat(
            [show_df[show_df["Country"] == highlight_country], show_df[show_df["Country"] != highlight_country]]
        )
    display_cols = {
        "Country": "Country",
        "Code": "Code",
        "Value2021_m": "2021 exports (US$M)",
        "Share2021": "2021 share",
        "Value2023_m": "2023 imports (US$M)",
        "Share2023": "2023 share",
        "abs_change_m": "Change (US$M)",
        "pct_change": "Change (%)",
        "status": "Status",
    }
    st.dataframe(
        show_df[list(display_cols.keys())]
        .rename(columns=display_cols)
        .style.format(
            {
                "2021 exports (US$M)": "{:,.0f}",
                "2021 share": "{:.2%}",
                "2023 imports (US$M)": "{:,.0f}",
                "2023 share": "{:.2%}",
                "Change (US$M)": "{:+,.0f}",
                "Change (%)": "{:+.1f}%",
            },
            na_rep="n/a",
        ),
        use_container_width=True,
        height=560,
        hide_index=True,
    )
    st.download_button(
        "Download this table as CSV",
        show_df.to_csv(index=False).encode("utf-8"),
        file_name="russia_trade_2021_vs_2023.csv",
        mime="text/csv",
    )

with tab_eufsu:
    st.subheader("EU <-> Former Soviet Union trade")
    st.markdown(
        """
        <div class="caveat">
        <b>Reading this section:</b> for 11 of the 12 former-Soviet countries here, this is
        <i>first-party</i> data on both sides &mdash; every EU member state's own customs
        reporting, for both what it exported and what it imported. The Baltic states (Estonia,
        Latvia, Lithuania) are counted as EU here, not as former-USSR. The 12 former-Soviet
        countries covered are Armenia, Azerbaijan, Belarus, Georgia, Kazakhstan, Kyrgyzstan,
        Moldova, <b>Russia</b>, Tajikistan, Turkmenistan, Ukraine and Uzbekistan. <b>Russia is the
        one exception:</b> since Russia stopped publishing detailed customs data after 2022, its
        figures here are <i>mirror data</i> &mdash; each EU country's own reporting of what it
        traded with Russia &mdash; same approach as the Russia tabs above, just restricted to EU
        partners. Russia's values are flagged wherever they appear below.
        </div>
        """,
        unsafe_allow_html=True,
    )

    eufsu_flow_label = st.radio(
        "Trade direction", ["EU exports to the former USSR", "EU imports from the former USSR"],
        index=0, horizontal=True, key="eufsu_flow_label",
    )
    eufsu_flow = "export" if eufsu_flow_label.startswith("EU exports") else "import"
    eufsu_flow_short = "exports" if eufsu_flow == "export" else "imports"
    eufsu_flow_verb = "exports to" if eufsu_flow == "export" else "imports from"
    eufsu_log = st.checkbox("Log-scale these maps", value=True, key="eufsu_log")

    st.markdown("#### Total EU trade with each former-Soviet country, 2021 vs 2023")
    st.caption(
        "Summed across all 27 EU reporters. Every map and bar chart in this section shares "
        "one fixed color/size scale (not just within a pair) - so a given dollar amount always "
        "looks the same everywhere, regardless of which chart or flow direction is on screen. "
        "Russia's figures are mirror data (see caveat above); the other 11 countries are "
        "first-party."
    )
    fsu_2021 = eu_fsu_agg_by_fsu(eu_fsu_df, 2021, eufsu_flow)
    fsu_2023 = eu_fsu_agg_by_fsu(eu_fsu_df, 2023, eufsu_flow)

    def _mirror_label(names):
        return names.apply(lambda n: f"{n} (mirror data)" if n == "Russia" else n)

    fc1, fc2 = st.columns(2)
    with fc1:
        st.markdown(f"**EU {eufsu_flow_verb} the former USSR, 2021**")
        st.plotly_chart(
            build_region_choropleth(
                fsu_2021["fsu_iso3"], fsu_2021["value_m"], _mirror_label(fsu_2021["fsu_country"]),
                f"EU {eufsu_flow_short}", eufsu_log, vmax_override=EU_FSU_GLOBAL_MAX_M,
            ),
            use_container_width=True, config={"displayModeBar": False},
        )
    with fc2:
        st.markdown(f"**EU {eufsu_flow_verb} the former USSR, 2023**")
        st.plotly_chart(
            build_region_choropleth(
                fsu_2023["fsu_iso3"], fsu_2023["value_m"], _mirror_label(fsu_2023["fsu_country"]),
                f"EU {eufsu_flow_short}", eufsu_log, vmax_override=EU_FSU_GLOBAL_MAX_M,
            ),
            use_container_width=True, config={"displayModeBar": False},
        )

    st.markdown(f"**Same totals, ranked - EU {eufsu_flow_short} by former-Soviet country (US$ million)**")
    st.caption("* = mirror data (Russia); the rest is first-party.")
    st.plotly_chart(
        build_ranked_bar(
            fsu_2021, fsu_2023, "fsu_country", eufsu_flow_short, EU_FSU_GLOBAL_MAX_M,
            height=420, mark_mirror=True,
        ),
        use_container_width=True, config={"displayModeBar": False},
    )

    st.markdown("---")
    st.markdown("#### Click an EU country to see its former-USSR trading partners, 2021 vs 2023")
    st.caption(
        "Click a country on either map below (or use the dropdown under them) to break down "
        "that EU country's trade with the 12 former-Soviet countries, as a % of its total - "
        "same country, both years, so you can see how the mix shifted. Russia's slice (marked "
        "with *) is mirror data; the rest is first-party."
    )

    eu_2021 = eu_fsu_agg_by_eu(eu_fsu_df, 2021, eufsu_flow)
    eu_2023 = eu_fsu_agg_by_eu(eu_fsu_df, 2023, eufsu_flow)

    default_country = eu_2023.iloc[0]["eu_country"] if len(eu_2023) else EU_COUNTRIES[0]
    if "eufsu_selected_country" not in st.session_state:
        st.session_state["eufsu_selected_country"] = default_country
    _sync_eu_click(eu_fsu_df, "eufsu_map_2021", "eufsu_selected_country", default_country)
    _sync_eu_click(eu_fsu_df, "eufsu_map_2023", "eufsu_selected_country", default_country)
    sel_country = st.session_state["eufsu_selected_country"]
    sel_iso3 = eu_fsu_df.loc[eu_fsu_df["eu_country"] == sel_country, "eu_iso3_map"].iloc[0]

    ec1, ec2 = st.columns(2)
    with ec1:
        st.markdown(f"**EU {eufsu_flow_verb} the former USSR, 2021**")
        render_clickable_map(
            build_region_choropleth(
                eu_2021["eu_iso3_map"], eu_2021["value_m"], eu_2021["eu_country"],
                f"Total {eufsu_flow_short}", eufsu_log, highlight_iso3=sel_iso3, vmax_override=EU_FSU_GLOBAL_MAX_M,
            ),
            "eufsu_map_2021",
        )
    with ec2:
        st.markdown(f"**EU {eufsu_flow_verb} the former USSR, 2023**")
        render_clickable_map(
            build_region_choropleth(
                eu_2023["eu_iso3_map"], eu_2023["value_m"], eu_2023["eu_country"],
                f"Total {eufsu_flow_short}", eufsu_log, highlight_iso3=sel_iso3, vmax_override=EU_FSU_GLOBAL_MAX_M,
            ),
            "eufsu_map_2023",
        )

    st.markdown(f"**Same totals, ranked - EU {eufsu_flow_short} by EU country (US$ million)**")
    st.plotly_chart(
        build_ranked_bar(
            eu_2021, eu_2023, "eu_country", eufsu_flow_short, EU_FSU_GLOBAL_MAX_M, height=680,
        ),
        use_container_width=True, config={"displayModeBar": False},
    )

    st.selectbox("Or pick an EU country:", EU_COUNTRIES, key="eufsu_selected_country")
    sel_country = st.session_state["eufsu_selected_country"]

    bc1, bc2 = st.columns(2)
    with bc1:
        breakdown_2021, total_2021_m = eu_country_breakdown(eu_fsu_df, sel_country, 2021, eufsu_flow)
        st.markdown(f"**{sel_country}'s {eufsu_flow_short}, 2021** - total ${total_2021_m:,.0f}M")
        st.plotly_chart(
            build_breakdown_bar(breakdown_2021, f"{sel_country}'s FSU {eufsu_flow_short}, 2021"),
            use_container_width=True, config={"displayModeBar": False},
        )
    with bc2:
        breakdown_2023, total_2023_m = eu_country_breakdown(eu_fsu_df, sel_country, 2023, eufsu_flow)
        st.markdown(f"**{sel_country}'s {eufsu_flow_short}, 2023** - total ${total_2023_m:,.0f}M")
        st.plotly_chart(
            build_breakdown_bar(breakdown_2023, f"{sel_country}'s FSU {eufsu_flow_short}, 2023"),
            use_container_width=True, config={"displayModeBar": False},
        )

    st.markdown("---")
    with st.expander("EU-FSU data table & methodology"):
        table_df = eu_fsu_df[eu_fsu_df["flow"] == eufsu_flow][
            ["eu_country", "fsu_country", "year", "value_th", "is_mirror"]
        ].rename(columns={
            "eu_country": "EU country", "fsu_country": "FSU country",
            "year": "Year", "value_th": "Value (US$ thousand)", "is_mirror": "Mirror data",
        }).sort_values("Value (US$ thousand)", ascending=False)
        st.dataframe(
            table_df.style.format({"Value (US$ thousand)": "{:,.0f}"}),
            use_container_width=True, height=400, hide_index=True,
        )
        st.download_button(
            "Download EU-FSU data as CSV",
            eu_fsu_df.to_csv(index=False).encode("utf-8"),
            file_name="eu_fsu_trade_2021_2023.csv",
            mime="text/csv",
        )
        st.markdown(
            """
            **Source:** World Bank WITS SDMX API, `tradestats-trade` datasource.
            For every EU member state, `reporter=all, partner={FSU country}, product=Total`,
            indicators `XPRT-TRD-VL` (that reporter's exports to the partner) and
            `MPRT-TRD-VL` (that reporter's imports from the partner), years 2021 and 2023.

            This is **first-party** data on both sides (each EU country's own reporting to
            Eurostat/UN Comtrade) for 11 of the 12 FSU countries. **Russia is the exception:**
            since Russia stopped reporting detailed customs data after 2022, its rows are
            **mirror data** &mdash; each EU country's own reporting of what it traded with
            Russia, for both 2021 and 2023, to keep the two years on the same basis. The
            "Mirror data" column in the table above flags exactly which rows this applies to
            (all 108 Russia rows, and only those).

            A handful of small EU-country/small-FSU-country pairs (19 of 1,296 possible
            combinations) have no reported value for a given year and flow - these all involve
            Malta, Cyprus, Croatia, Hungary or Latvia paired with Tajikistan, Turkmenistan,
            Uzbekistan, Armenia, Azerbaijan or Belarus, consistent with genuinely negligible
            trade rather than a data gap. Russia has no such gaps - full 27x2x2 coverage.
            """
        )

with tab_method:
    st.subheader("How this data was pulled")
    st.markdown(
        """
        All four datasets come from the **WITS (World Integrated Trade Solution) SDMX API**,
        operated by the World Bank on top of UN Comtrade.

        **Exports (2021 vs 2023 maps, Change map / Top movers when "Russia's exports" is selected):**
        - **Exports 2021** &mdash; `reporter=RUS, partner=all, product=Total, year=2021,
          indicator=XPRT-TRD-VL`. This is Russia's own reporting: the last full year
          before Russia stopped publishing detailed customs data.
        - **Imports 2023 (mirror)** &mdash; `reporter=all, partner=RUS, product=Total, year=2023,
          indicator=MPRT-TRD-VL`. Since Russia doesn't report anymore, this flips the
          query: every *other* country's own official statistics on what it imported
          from Russia ("mirror data") &mdash; the standard, UN Comtrade-endorsed way to
          reconstruct a non-reporting country's trade.

        **Imports (Change map / Top movers when "Russia's imports" is selected):** the mirror
        image of the above, same methodology, opposite direction.
        - **Imports 2021** &mdash; `reporter=RUS, partner=all, product=Total, year=2021,
          indicator=MPRT-TRD-VL`. Russia's own reporting on what it imported from each partner.
        - **Exports 2023 (mirror)** &mdash; `reporter=all, partner=RUS, product=Total, year=2023,
          indicator=XPRT-TRD-VL`. Every other country's own statistics on what it exported to
          Russia.

        **General notes (apply to all four):**
        - **Units**: all sheets are in US$ thousand, current prices &mdash; no unit
          conversion applied, so any two of them are directly comparable line by line (modulo
          the reporting-method caveat above).
        - **Region rows** (EAS, ECS, LCN, MEA, NAC, OAS, SAS, SSF, WLD, EUN) are
          pre-aggregated region/bloc totals from the same API response. They are
          excluded from the maps and country table here to avoid double-counting.
        - A handful of countries use **legacy WITS/Comtrade codes** that don't match
          current ISO-3166 alpha-3 (e.g. `ROM`->`ROU` Romania, `SER`->`SRB` Serbia,
          `SUD`->`SDN` Sudan, `ZAR`->`COD` DR Congo, `TMP`->`TLS` Timor-Leste,
          `MNT`->`MNE` Montenegro). These are remapped for the choropleth so they
          render correctly.
        - **The 2023 imports-mirror data (exports-to-Russia) has a bigger reporting gap** than
          the 2023 exports-mirror data (imports-from-Russia): the region aggregates the API
          returns only account for about 84% of its own reported world total, versus about
          99.8% on the exports-mirror side, and 90 countries that had a 2021 import record drop
          out of the 2023 mirror data entirely (vs. about 20 on the exports side). This is
          consistent with countries under-reporting or delaying disclosure of goods shipped to
          a sanctioned country more than they under-report goods bought from it - not a sign
          the underlying trade stopped. Treat imports-mirror totals as a reasonable floor, not
          a precise figure.
        """
    )
    st.caption(
        "Precision note: the 2021 export figures were cross-checked line-by-line "
        "against independently verified figures for China, Netherlands, Germany, "
        "Turkey, Belarus, UK, Italy, Kazakhstan, USA and South Korea, and matched exactly. "
        "The imports dataset was validated the same way its own region-aggregate rows sum to "
        "each dataset's reported world total: within 0.2% for Russia's own 2021 reporting, "
        "consistent with the exports side, but the country-level rows in the 2023 "
        "imports-mirror data only account for about 84% of its region aggregates - see the "
        "reporting-gap note above."
    )

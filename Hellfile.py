from hellbox import Hellbox
from hellbox.jobs.afdko import MakeOTF, Otf2Ttf, TtfComponentizer

with Hellbox("build") as task:
    task.describe("Build static OTF and TTF instances from UFO sources.")
    task.clean("target/OTF")
    task.clean("target/TTF")
    task.read(
        "Upright/Instances/*/font.ufo",
        "Italic/Instances/*/font.ufo",
    ) >> MakeOTF(release=True, filter_glyphs=True, omit_mac_names=True) \
      >> task.write("target/OTF") \
      >> Otf2Ttf() \
      >> TtfComponentizer() \
      >> task.write("target/TTF")

Hellbox.default = "build"

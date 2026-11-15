"""Replace only the sharp title texture; preserve model geometry and animations."""
import struct
from PIL import Image

RESOURCE=0x21320400
HEADER=0x180

def pixels_range(model):
    width,height=struct.unpack_from('>HH',model,HEADER)
    assert (width,height,model[HEADER+4])==(514,70,16)
    at=HEADER+struct.unpack_from('>I',model,HEADER+40)[0]
    size=((width+3)//4)*((height+3)//4)*32
    assert at+size<=len(model)
    return width,height,at,size

def encode_rgb5a3(image):
    w,h=image.size;px=image.load();out=bytearray()
    for y in range(0,h,4):
        for x in range(0,w,4):
            for dy in range(4):
                for dx in range(4):
                    r,g,b,a=px[x+dx,y+dy] if x+dx<w and y+dy<h else (0,0,0,0)
                    if a>=224:value=0x8000|((r*31+127)//255)<<10|((g*31+127)//255)<<5|((b*31+127)//255)
                    else:value=((a*7+127)//255)<<12|((r*15+127)//255)<<8|((g*15+127)//255)<<4|((b*15+127)//255)
                    out.extend(struct.pack('>H',value))
    return bytes(out)

def prepare(model,image_path):
    width,height,at,size=pixels_range(model)
    image=Image.open(image_path).convert('RGBA');box=image.getchannel("A").point(lambda a:255 if a>=32 else 0).getbbox()
    if not box:raise ValueError('Empty title artwork')
    # Technical export into the fixed native texture canvas. The approved
    # composited artwork is generated separately, never drawn by this encoder.
    image=image.crop(box);image.thumbnail((width-4,height-4),Image.Resampling.LANCZOS)
    canvas=Image.new('RGBA',(width,height));canvas.paste(image,((width-image.width)//2,(height-image.height)//2))
    texture=encode_rgb5a3(canvas);assert len(texture)==size
    out=model[:at]+texture+model[at+size:]
    assert len(out)==len(model) and out[:at]==model[:at] and out[at+size:]==model[at+size:]
    return out,canvas,{'texture_dimensions':[width,height],'texture_header':hex(HEADER),'pixel_offset':at,
                      'geometry_and_animation_bytes_preserved':True,'gpu_timing_tested':False}

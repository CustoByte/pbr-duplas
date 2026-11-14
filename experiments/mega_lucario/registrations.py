"""Cumulative Mega registrations, preserving the installed Snivy and all old rows."""
import struct
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'mod-source'),str(ROOT/'expansion'),str(ROOT/'experiments/snivy')]
from translation.messages import read_messages,write_messages,readable,encoded
from pkx_reference import scene_inventory
from catalog import append_archive
from encounter_expansion import rebuild_archive
from prepare_campaign_doubles import read_archive,word

SPECIES,MODEL,ARCHIVE=502,671,0x2001
NORMAL,SHINY,FACE,BODY=0x73EB0400,0x63EB0400,0x7BEB0C00,0x6BEB0C00
STATS,MODELS,MAP,MESSAGES=0x00810200,0x00800200,0x008B0000,0x27C10000

def append(table,count,stride,row):
 if struct.unpack_from('>II',table)!=(count,stride) or len(row)!=stride:raise ValueError('Unexpected cumulative table')
 if struct.unpack_from('>III',table,16)!=(48,count*stride,len(table)):raise ValueError('Unexpected table header')
 end=48+count*stride
 out=bytearray(table[:end]+row+table[end:]);struct.pack_into('>I',out,0,count+1);struct.pack_into('>II',out,20,(count+1)*stride,len(out))
 assert out[48:end]==table[48:end] and out[end+stride:]==table[end:]
 return bytes(out)

def prepare(resources,messages,sdr,reference):
 stride,count=struct.unpack_from('>II',resources[MAP])
 if stride!=4 or count!=21775:raise ValueError('Expected installed Snivy name map')
 header,rows=read_messages(messages)
 if any(readable(r)=='{F001}{F101}MEGA LUCARIO' for r in rows):raise ValueError('Mega already registered')
 header=bytearray(header);struct.pack_into('>I',header,4,len(rows)+1)
 new_messages=write_messages(bytes(header),rows+[encoded('{F001}{F101}MEGA LUCARIO')])
 mapping=bytearray(resources[MAP]+struct.pack('>HH',1,len(rows)+1));struct.pack_into('>I',mapping,4,count+1)
 scene=scene_inventory(sdr);nodes={n['name']:n['index'] for n in scene['nodes']};actions={a['name']:a['index'] for a in scene['actions']}
 native=scene_inventory(dict(read_archive(reference))[0x09770400]);native_nodes={n['index']:n['name'] for n in native['nodes']}
 base=resources[MODELS][48+569*72:48+570*72];model=bytearray(base)
 old_ids={struct.unpack_from('>I',resources[MODELS],48+i*72+o)[0] for i in range(671) for o in (8,12)}
 if old_ids&{NORMAL,SHINY}:raise ValueError('Model identity collision')
 struct.pack_into('>III',model,4,ARCHIVE,NORMAL,SHINY);struct.pack_into('>H',model,20,SPECIES)
 for i,n in enumerate(base[25:50]):model[25+i]=0 if n==0 else nodes[native_nodes[n]]
 for i,a in enumerate(base[50:72]):model[50+i]=actions[native['actions'][a]['name']]
 stats=bytearray(resources[STATS][48+448*52:48+449*52])
 struct.pack_into('>HH',stats,20,13,575);struct.pack_into('>HHH',stats,24,count+1,count+1,MODEL)
 stats[30:36]=bytes((70,145,88,112,140,70));stats[36:38]=bytes((1,8));stats[48:50]=bytes((91,0))
 replacements={MAP:bytes(mapping),STATS:append(resources[STATS],502,52,bytes(stats)),MODELS:append(resources[MODELS],671,72,bytes(model))}
 replacements[0x00820200]=append(resources[0x00820200],502,42,bytes(42))
 levels=resources[0x12A90200][48+448*80:48+449*80]
 replacements[0x12A90200]=append(resources[0x12A90200],502,80,levels)
 icon=struct.pack('>4I',FACE,BODY,FACE,BODY)
 if any(struct.pack('>I',v) in resources[0x1D9D0200][48:] for v in (FACE,BODY)):raise ValueError('Icon identity collision')
 replacements[0x1D9D0200]=append(resources[0x1D9D0200],563,16,icon)
 replacements[0x007D0200]=append(resources[0x007D0200],502,8,struct.pack('>IHH',SPECIES,563,2))
 replacements[0x16410200]=append(resources[0x16410200],502,12,struct.pack('>IHHHH',SPECIES,563,1,0,0))
 assert read_messages(new_messages)[1][:-1]==rows
 return replacements,new_messages

def model_package(reference,sdr):
 # Normal appearance is deliberately used for either shiny flag until a supplied
 # shiny texture is available; this prevents a missing-resource wait.
 original=read_archive(reference)
 if [r[0] for r in original]!=[0x09770400,0x20340400]:raise ValueError('Expected Lucario package')
 out=bytearray(rebuild_archive(reference,{key:sdr for key,_ in original}));table=word(out,word(out,24))
 for i,rid in enumerate((NORMAL,SHINY)):struct.pack_into('>I',out,word(out,table+4*i),rid)
 assert read_archive(out)==[(NORMAL,sdr),(SHINY,sdr)]
 return bytes(out)

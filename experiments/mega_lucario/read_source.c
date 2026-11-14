/* Private FBX intermediate reader. Build against MIT ufbx v0.17.1.
 * Does not produce game-ready SDR or change a game archive. */
#include "ufbx.h"
#include <stdio.h>
#include <stdlib.h>
#ifdef _WIN32
#include <windows.h>
#include <wchar.h>
#endif
static FILE *out;
static void string(ufbx_string s) {
 fputc('"',out); for(size_t i=0;i<s.length;i++) { unsigned char c=s.data[i];
 if(c=='"'||c=='\\')fprintf(out,"\\%c",c); else if(c<32)fprintf(out,"\\u%04x",c);else fputc(c,out); } fputc('"',out);
}
static void vec(ufbx_vec3 v) {fprintf(out,"[%.17g,%.17g,%.17g]",v.x,v.y,v.z);}
static void mat(ufbx_matrix m) {fputc('[',out);for(int i=0;i<4;i++){if(i)fputc(',',out);vec(m.cols[i]);}fputc(']',out);}
static int run(int argc,char **argv) {
 if(argc!=3){fprintf(stderr,"usage: read_source input.fbx private-output.json\n");return 2;}
 ufbx_load_opts opts={0};ufbx_error error;
 ufbx_scene *s=ufbx_load_file(argv[1],&opts,&error);
 if(!s){char b[2048];ufbx_format_error(b,sizeof(b),&error);fprintf(stderr,"%s\n",b);return 1;}

#ifdef _WIN32
 int wide_count=MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,argv[2],-1,NULL,0);
 wchar_t *wide_output=(wchar_t *)malloc((size_t)wide_count*sizeof(wchar_t));
 if(!wide_count||!wide_output){ufbx_free_scene(s);return 1;}
 MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,argv[2],-1,wide_output,wide_count);
 out=_wfopen(wide_output,L"w");free(wide_output);
#else
 out=fopen(argv[2],"w");
#endif
if(!out){ufbx_free_scene(s);return 1;}
 fprintf(out,"{\"schema\":1,\"nodes\":[");
 for(size_t i=0;i<s->nodes.count;i++){ufbx_node*n=s->nodes.data[i];if(i)fputc(',',out);
 fprintf(out,"{\"id\":%u,\"name\":",n->typed_id);string(n->name);
 fprintf(out,",\"parent\":%d,\"world\":",n->parent?(int)n->parent->typed_id:-1);mat(n->node_to_world);
 fprintf(out,",\"geometry\":");mat(n->geometry_to_world);fprintf(out,"}");}
 fprintf(out,"],\"meshes\":[");
 for(size_t mi=0;mi<s->meshes.count;mi++){ufbx_mesh*m=s->meshes.data[mi];if(mi)fputc(',',out);
 fprintf(out,"{\"name\":");string(m->name);fprintf(out,",\"node\":%u,\"positions\":[",m->instances.data[0]->typed_id);
 for(size_t i=0;i<m->vertices.count;i++){if(i)fputc(',',out);vec(m->vertices.data[i]);}
 fprintf(out,"],\"indices\":[");for(size_t i=0;i<m->vertex_indices.count;i++){if(i)fputc(',',out);fprintf(out,"%u",m->vertex_indices.data[i]);}
 fprintf(out,"],\"faces\":[");for(size_t i=0;i<m->faces.count;i++){if(i)fputc(',',out);fprintf(out,"[%u,%u]",m->faces.data[i].index_begin,m->faces.data[i].num_indices);}
 fprintf(out,"],\"normals\":[");for(size_t i=0;i<m->num_indices;i++){if(i)fputc(',',out);vec(ufbx_get_vertex_vec3(&m->vertex_normal,i));}
 fprintf(out,"],\"uvs\":[");for(size_t i=0;i<m->num_indices;i++){if(i)fputc(',',out);ufbx_vec2 v=ufbx_get_vertex_vec2(&m->vertex_uv,i);fprintf(out,"[%.17g,%.17g]",v.x,v.y);}
 fprintf(out,"],\"materials\":[");for(size_t i=0;i<m->materials.count;i++){if(i)fputc(',',out);ufbx_material*a=m->materials.data[i];fprintf(out,"{\"name\":");string(a->name);fprintf(out,",\"textures\":[");for(size_t j=0;j<a->textures.count;j++){if(j)fputc(',',out);string(a->textures.data[j].texture->filename);}fprintf(out,"]}");}
 fprintf(out,"],\"face_materials\":[");for(size_t i=0;i<m->face_material.count;i++){if(i)fputc(',',out);fprintf(out,"%u",m->face_material.data[i]);}
 fprintf(out,"],\"clusters\":[");size_t ci=0;
 for(size_t si=0;si<m->skin_deformers.count;si++){ufbx_skin_deformer*skin=m->skin_deformers.data[si];for(size_t j=0;j<skin->clusters.count;j++){ufbx_skin_cluster*c=skin->clusters.data[j];if(ci++)fputc(',',out);
 fprintf(out,"{\"node\":%u,\"bind_world\":",c->bone_node->typed_id);mat(c->bind_to_world);fprintf(out,",\"geometry_to_bone\":");mat(c->geometry_to_bone);
 fprintf(out,",\"weights\":[");for(size_t k=0;k<c->num_weights;k++){if(k)fputc(',',out);fprintf(out,"[%u,%.17g]",c->vertices.data[k],c->weights.data[k]);}fprintf(out,"]}");}}
 fprintf(out,"]}");}
 fprintf(out,"],\"takes\":[");for(size_t i=0;i<s->anim_stacks.count;i++){if(i)fputc(',',out);ufbx_anim_stack*a=s->anim_stacks.data[i];fprintf(out,"{\"name\":");string(a->name);fprintf(out,",\"start\":%.17g,\"end\":%.17g}",a->time_begin,a->time_end);}fprintf(out,"]}\n");
 int failed=ferror(out);if(fclose(out))failed=1;ufbx_free_scene(s);return failed?1:0;
}

#ifdef _WIN32
int wmain(int argc,wchar_t **wide_args) {
 if(argc!=3)return 2;
 char *args[3]={0};
 for(int i=0;i<3;i++){
  int n=WideCharToMultiByte(CP_UTF8,0,wide_args[i],-1,NULL,0,NULL,NULL);
  args[i]=(char *)malloc((size_t)n);
  if(!n||!args[i])return 1;
  WideCharToMultiByte(CP_UTF8,0,wide_args[i],-1,args[i],n,NULL,NULL);
 }
 int result=run(argc,args);for(int i=0;i<3;i++)free(args[i]);return result;
}
#else
int main(int argc,char **argv){return run(argc,argv);}
#endif

"""Host tests of the actual parser/writer code, with flash and UBI I/O mocked."""
from pathlib import Path
import os
import tempfile
import re
import subprocess

ROOT = Path(os.environ['CT3003_TEST_FIXTURES']).resolve()
SRC = Path(__file__).resolve().parents[2] / 'uboot-mtk-20250711'
_tmp = tempfile.TemporaryDirectory(prefix='ct3003-host-')
OUT = Path(_tmp.name)
OUT.mkdir(exist_ok=True)

def function(text, name):
    matches = list(re.finditer(r'^(?:static )?(?:int|bool|void) (?:__init )?' + name + r'\(', text, re.M))
    m = (matches[-1] if name == 'ubi_mtd_param_parse' else matches[0]) if matches else None
    assert m, name
    end = text.index('\n}', m.start()) + 2
    result = text[m.start():end]
    if name == 'ubi_mtd_param_parse':
        result = result.replace('#endif\n', '', 1)
    return result + '\n'

mtd = (SRC / 'board/mediatek/common/mtd_helper.c').read_text()
image = (SRC / 'board/mediatek/common/image_helper.c').read_text()
untar = (SRC / 'board/mediatek/common/untar.c').read_text()
header = (SRC / 'board/mediatek/common/untar.h').read_text()
image_header = (SRC / 'board/mediatek/common/image_helper.h').read_text()
ubi_build = (SRC / 'drivers/mtd/ubi/build.c').read_text()
ubi_cmd = (SRC / 'cmd/ubi.c').read_text()
strto = (SRC / 'lib/strto.c').read_text()

preamble = r'''
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <errno.h>
#include <assert.h>
#include <zlib.h>
#include <limits.h>
#include <ctype.h>
typedef unsigned int uint;
typedef unsigned long ulong;
typedef unsigned char u8, __u8;
typedef uint32_t u32, __be32;
typedef unsigned long long u64;
#define ENOTSUPP ENOTSUP
#define MTD_NANDFLASH 1
#define MTD_MLCNANDFLASH 2
struct legacy_img_hdr { char x[64]; };
#define CONFIG_CMD_UBI 1
#define CONFIG_MEDIATEK_MULTI_MTD_LAYOUT 1
#define CONFIG_FIT 1
#define CONFIG_IS_ENABLED(x) 0
#define IS_ENABLED(x) 0
#define IS_ERR_OR_NULL(x) (!(x))
#define PART_KERNEL_NAME "kernel"
#define PART_ROOTFS_NAME "rootfs"
#define PART_ROOTFS_DATA_NAME "rootfs_data"
#define PART_UBI_NAME "ubi"
#define PART_FIT_NAME "fit"
#define UBI_MOUNT_RECREATE true
#define debug(...) do{}while(0)
#define cprintln(level,...) printf(__VA_ARGS__)
#define ALIGN(x,a) (((x)+(a)-1)&~((a)-1))
#define __init
#define __UBOOT__ 1
#define fallthrough __attribute__((fallthrough))
#define pr_err(...) printf(__VA_ARGS__)
#define pr_warn(...) printf(__VA_ARGS__)
#define MTD_PARAM_LEN_MAX 64
#define MTD_PARAM_MAX_COUNT 4
#define MAX_MTD_UBI_BEB_LIMIT 768
#define UBI_MAX_DEVICES 32
#define UBI_DEV_NUM_AUTO -1
struct mtd_dev_param {char name[MTD_PARAM_LEN_MAX];int ubi_num,vid_hdr_offs,max_beb_per1024;};
struct kernel_param;
static int mtd_devs;
static struct mtd_dev_param mtd_dev_param[UBI_MAX_DEVICES];
int ubi_mtd_param_parse(const char *,struct kernel_param *);
int ubi_mtd_param_validate(const char *);
static ulong simple_strtoul(const char *,char **,uint);
static u32 be32_to_cpu(u32 n) { return __builtin_bswap32(n); }
static u32 get_unaligned_le32(const void *p) { u32 x;memcpy(&x,p,4);return x; }
static u64 get_unaligned_le64(const void *p) { u64 x;memcpy(&x,p,8);return x; }
static int is_power_of_2(u32 x) {return x && !(x&(x-1));}
static u32 crc32_no_comp(u32 n,const u8 *p,size_t l){return crc32(n^0xffffffff,p,l)^0xffffffff;}
struct fdt_header {char x[40];};
#define IMAGE_FORMAT_FIT 1
static int genimg_get_format(const void *p){return be32_to_cpu(get_unaligned_le32(p))==0xd00dfeed?1:0;}
static u32 fit_get_size(const void *p){return be32_to_cpu(get_unaligned_le32(p+4));}
struct mtd_info {const char *name;u64 size,offset;u32 erasesize,erasesize_mask;struct mtd_info *parent;int type;u32 writesize;};
struct erase_info {struct mtd_info *mtd;u64 addr,len;};
static struct mtd_info master={"nmbm0",0,0,131072,131071,0};
static struct mtd_info fw={"ubi",33554432,5767168,131072,131071,&master,0,2048};
static struct mtd_info backup={"Config_backup",4194304,72876032,131072,131071,&master,0,2048};
static int backup_erased,env_saves,env_save_rc;
static bool mtd_layout_save_pending;
static char mtd_layout_label[32]="stock";
static int env_save(void){env_saves++;return env_save_rc;}
static int env_set(const char *k,const char *v){return 0;}
static const char *layout_override;
static int small=1,step,erase_calls,writes,attached,create_overlay,create_conf,conf_exists;
static int erase_fail,bad_block=-1,last_erase_step,last_attach_step,last_write_step;
static u64 erased_bytes;
typedef int ofnode;
static const char *get_mtd_layout_label(void){return small?"stock":"big";}
static ofnode ofnode_path(const char *p){return 1;}
static bool ofnode_valid(ofnode n){return n!=0;}
#define ofnode_for_each_subnode(l,n) for(l=2;l<=3;l++)
static const char *ofnode_read_string(ofnode n,const char *p){return !strcmp(p,"label")?(n==2?"big":"stock"):"ubi";}
static bool ofnode_read_bool(ofnode n,const char *p){return !strcmp(p,"erase-before-fit-upgrade")?n==2:n==3;}
struct ubi_device {struct mtd_info *mtd;};
static struct ubi_device mock_ubi, *ubi, *ubi_devices[1]={&mock_ubi};
static void ubi_detach(void){attached=0;ubi=NULL;mtd_devs=0;++step;}
static void gen_mtd_probe_devices(void){assert(!attached);++step;}
static const char *env_get(const char *p){if(layout_override&&!strcmp(p,"mtd_layout"))return layout_override;return !strcmp(p,"factory_part")?"ubi":(!strcmp(p,"mtd_layout")||!strcmp(p,"mtd_layout_label"))?"stock":NULL;}
static struct mtd_info *get_mtd_device_nm(const char *p){return !strcmp(p,"ubi")?&fw:!strcmp(p,"Config_backup")?&backup:NULL;}
static void put_mtd_device(struct mtd_info *p){}
static int mtd_block_isbad(struct mtd_info *m,u64 a){return (int)(a/m->erasesize)==bad_block;}
static int mtd_erase(struct mtd_info *m,struct erase_info *e){assert(e->addr+e->len<=m->size);assert(!attached);++erase_calls;if(m==&backup)backup_erased=1;erased_bytes+=e->len;last_erase_step=++step;return erase_fail?-EIO:0;}
static int mtd_write_skip_bad(struct mtd_info *m,u64 a,size_t l,u64 max,void *r,const void *d,bool v){assert(l<=m->size);assert(erase_calls);++writes;last_write_step=++step;return 0;}
static bool verify_standalone_image_ram(const void *d,size_t n){return genimg_get_format(d)==1;}
static void mtd_probe_devices(void){}
#define IS_ERR(x) (!(x))
static void led_activity_blink(void){}
static void led_activity_off(void){}
static int conf_lebs,cold_fail,fw_attaches,backup_attaches;
static int ubi_init(void){assert(mtd_devs==1);struct mtd_dev_param*p=&mtd_dev_param[0];mock_ubi.mtd=get_mtd_device_nm(p->name);if(mock_ubi.mtd==&fw&&++fw_attaches==2&&cold_fail==1)return -EIO;if(mock_ubi.mtd==&backup&&++backup_attaches==3&&cold_fail==2)return -EIO;if(mock_ubi.mtd==&backup){assert(p->max_beb_per1024==1);conf_lebs=32-4-(960*p->max_beb_per1024+1023)/1024;if(!conf_exists&&!backup_erased)return -EINVAL;}attached=mock_ubi.mtd==&fw?1:2;last_attach_step=++step;return 0;}
static int fit_written,empty_vols,remove_fail,read_calls;
struct ubi_volume {int vol_id;};
static struct ubi_volume overlay={2}, conf={0};
static struct ubi_volume *ubi_find_volume(const char *n){if(!strcmp(n,"conf"))return conf_exists?&conf:NULL;if(empty_vols)return !strcmp(n,"fit")&&fit_written?&overlay:!strcmp(n,"rootfs_data")&&create_overlay?&overlay:NULL;return &overlay;}
static int remove_ubi_volume(const char *n){assert(ubi_find_volume(n));++step;return remove_fail?-EIO:0;}
static int create_ubi_volume(const char *n,u64 z,int id,bool resize){if(!strcmp(n,"rootfs_data")){create_overlay++;assert(id==2||id==-1);}if(!strcmp(n,"conf")){assert(conf_lebs>=17);create_conf++;conf_exists=1;}++step;return 0;}
static int update_ubi_volume(const char *n,int id,const void *d,size_t z){assert(attached==1);assert(erase_calls);if(!strcmp(n,"fit"))fit_written=1;++writes;last_write_step=++step;return 0;}
static int ubi_check_reserved_volumes(bool x){return 0;}
static int write_ubi1_image(){abort();}
static int write_ubi1_tar_image(){abort();}
static int write_ubi2_tar_image_separate(){abort();}

struct slot {const char *kernel,*rootfs,*rootfs_data;};
static struct slot dual_boot_slots[2];
static u32 dual_boot_get_next_slot(void){return 0;}
static int mtd_dual_boot_post_upgrade(){abort();}
#define PART_NVRAM_NAME "nvram"
#define PART_JFFS2_NAME "jffs2"
#define NVRAM_VOLUME_SIZE 126976
#define CONFIG_MTK_DEFAULT_FIT_BOOT_CONF ""
static const char *ubi_image_vol;
static unsigned char read_buff[64];
static ulong get_load_addr(void){return (ulong)read_buff;}
static void bootargs_reset(void){}
static void fdtargs_reset(void){}
static int mtd_set_fdtargs_basic(void){return 0;}
static int boot_from_mem(ulong a){return 0;}
static int read_ubi_volume(const char*n,void*d,size_t z){assert(ubi_find_volume(n));read_calls++;return 0;}
'''

preamble += "\nstatic int mtd_write_skip_bad_common(struct mtd_info*m,u64 a,size_t l,u64 max,size_t*r,const void*d,bool v,bool trim){assert(trim);return mtd_write_skip_bad(m,a,l,max,r,d,v); }\n"
code = preamble
code += strto[strto.index('static const char *_parse_integer_fixup_radix'):strto.index('ulong simple_strtoul(')]
code += strto[strto.index('ulong simple_strtoul('):strto.index('\n}',strto.index('ulong simple_strtoul('))+2].replace('ulong simple_strtoul(', 'static ulong simple_strtoul(') + '\n'
code += function(ubi_build, 'bytes_str_to_int')
code += function(ubi_build, 'kstrtoint')
code += function(ubi_build, 'ubi_mtd_param_parse_one')
code += function(ubi_build, 'ubi_mtd_param_validate')
code += function(ubi_build, 'ubi_mtd_param_parse')
code += function(ubi_cmd, 'ubi_dev_scan')
code += function(ubi_cmd, 'ubi_part')
code += re.sub(r'^#include.*\n', '', header, flags=re.M)
code += re.sub(r'^#include.*\n', '', image_header, flags=re.M)
code += re.sub(r'^#include.*\n', '', untar, flags=re.M)
code += image[image.index('struct rootfs_info'):image.index('int find_ubi_start(')]
code += function(image, 'parse_image_ubi1')
code += function(image, 'parse_image_ubi2_ram')
code += function(image, 'parse_image_ram')
code += function(mtd, 'mtd_erase_skip_bad')
code += function(mtd, 'mtd_firmware_layout_flag')
code += function(mtd, 'mtd_firmware_full_erase')
code += function(mtd, 'mtd_erase_firmware')
code += function(mtd, 'mtd_update_generic')
code += function(mtd, 'mount_ubi_params')
code += function(mtd, 'mount_ubi')
code += function(mtd, 'mtd_update_ubi_image')
code += function(mtd, 'write_stock_ubi_image')
code += function((SRC/'failsafe/modules/upgrade.c').read_text(), 'failsafe_save_mtd_layout')
code += function(mtd, 'write_ubi2_tar_image')
code += function(mtd, 'write_ubi_itb_image')
code += function(mtd, 'boot_from_ubi')
code += function(mtd, 'mtd_upgrade_image')
code += r'''
static void reset_state(void){step=erase_calls=writes=attached=create_overlay=create_conf=conf_exists=erase_fail=0;erased_bytes=0;bad_block=-1;backup_erased=env_saves=env_save_rc=0;mtd_devs=0;ubi=NULL;conf_lebs=cold_fail=fw_attaches=backup_attaches=0;small=1;fit_written=empty_vols=remove_fail=read_calls=0;fw.size=33554432;fw.name="ubi";layout_override=NULL;}
static void *load(const char *p,size_t *n){FILE*f=fopen(p,"rb");assert(f);fseek(f,0,SEEK_END);*n=ftell(f);rewind(f);void*d=malloc(*n);assert(fread(d,1,*n,f)==*n);fclose(f);return d;}
int main(int argc,char **argv){
 int n=777;assert(!kstrtoint("1",10,&n)&&n==1);assert(!kstrtoint("2147483647",10,&n)&&n==INT_MAX);assert(!kstrtoint("-2147483648",10,&n)&&n==INT_MIN);assert(!kstrtoint("+1\n",10,&n)&&n==1);assert(!kstrtoint("0x20",0,&n)&&n==32);assert(!kstrtoint("037",0,&n)&&n==31);assert(!kstrtoint("z",36,&n)&&n==35);assert(kstrtoint("0x20",8,&n)==-EINVAL);assert(kstrtoint("2147483648",10,&n)==-ERANGE);assert(kstrtoint("-2147483649",10,&n)==-ERANGE);assert(kstrtoint("18446744073709551616",10,&n)==-ERANGE);assert(kstrtoint("1junk",10,&n)==-EINVAL);assert(kstrtoint("",10,&n)==-EINVAL);puts("PASS real kstrtoint: stores output, returns zero, validates sign, radix, range and trailing input");
 reset_state();assert(!ubi_mtd_param_validate("Config_backup,0,1")&&mtd_devs==0);assert(!ubi_mtd_param_parse("Config_backup,0,1",NULL)&&mtd_devs==1&&mtd_dev_param[0].max_beb_per1024==1&&mtd_dev_param[0].vid_hdr_offs==0&&mtd_dev_param[0].ubi_num==-1);assert(!ubi_mtd_param_parse("ubi,2048,20,1",NULL)&&mtd_dev_param[1].ubi_num==1);assert(ubi_mtd_param_parse("Config_backup,0,1x",NULL)==-EINVAL&&mtd_devs==2);assert(ubi_mtd_param_validate("Config_backup,0,769")==-EINVAL);assert(ubi_mtd_param_validate("Config_backup,0,-1")==-EINVAL);puts("PASS real UBI parameter parser: 0,1 accepted, failed parsing does not register a device");
 reset_state();assert(mount_ubi_params(&backup,true,"0,1x")==-EINVAL&&erase_calls==0&&attached==0&&mtd_devs==0);assert(mount_ubi_params(&backup,true,"0,769")==-EINVAL&&erase_calls==0);puts("PASS invalid attach parameters cannot erase Config_backup");
 size_t tn,un;u8*t=load(argv[1],&tn),*u=load(argv[2],&un);struct owrt_image_info ii={0};
 assert(!parse_image_ram(t,tn,131072,&ii)&&ii.type==IMAGE_TAR);
 assert(!parse_image_ram(u,un,131072,&ii)&&ii.type==IMAGE_UBI2&&ii.ubi_size==un);
 reset_state();attached=1;assert(!mtd_upgrade_image(t,tn));assert(erased_bytes==33554432&&writes==2&&create_overlay==1);assert(last_erase_step<last_attach_step&&last_attach_step<last_write_step);puts("PASS supplied 1.bin: detach, erase 32MiB, attach, write kernel/rootfs, create overlay");
 reset_state();attached=1;assert(!mtd_upgrade_image(u,un));assert(erased_bytes==33554432+4194304&&writes==1&&create_overlay==1&&create_conf==1);assert(!attached);puts("PASS supplied stock UBI: write/verify, recreate overlay, initialize conf");
 reset_state();conf_exists=1;assert(!mtd_upgrade_image(u,un));assert(create_conf==0);puts("PASS existing conf retained");
 reset_state();bad_block=7;assert(!mtd_upgrade_image(t,tn));assert(erased_bytes==33554432-131072);puts("PASS physical bad block skipped within stock boundary");
 reset_state();erase_fail=1;assert(mtd_upgrade_image(t,tn)<0&&writes==0);puts("PASS erase failure prevents write");
 reset_state();assert(mtd_update_generic(&fw,u,33554433,true)<0&&erase_calls==0);puts("PASS oversize rejected before erase");
 reset_state();assert(mtd_upgrade_image(t,600)<0&&erase_calls==0);puts("PASS truncated tar rejected before erase");
 reset_state();small=0;assert(!mtd_update_generic(&fw,u,131072,true));assert(erased_bytes==131072);puts("PASS large layout keeps existing erase behavior");
 reset_state();mtd_layout_save_pending=true;assert(!failsafe_save_mtd_layout()&&env_saves==1&&!mtd_layout_save_pending);mtd_layout_save_pending=true;env_save_rc=-EIO;assert(failsafe_save_mtd_layout()==-EIO&&mtd_layout_save_pending);puts("PASS layout save is mandatory and save errors propagate before HTTP success");
 reset_state();cold_fail=1;assert(mtd_upgrade_image(u,un)!=0&&!attached&&fw_attaches==2);puts("PASS firmware UBI reattach failure prevents success");
 reset_state();cold_fail=2;assert(mtd_upgrade_image(u,un)!=0&&!attached&&backup_attaches==3&&fw_attaches==1);puts("PASS Config_backup reattach failure prevents success");

 size_t fn;u8*f=load(argv[3],&fn);parse_image_ram(f,fn,131072,&ii);assert(ii.header_type==HEADER_FIT);
 reset_state();small=0;fw.size=0x6e80000;empty_vols=1;assert(!mtd_upgrade_image(f,fn));assert(erased_bytes==0x6e80000&&writes==1&&create_overlay==1&&!attached&&fw_attaches==2);assert(last_erase_step<last_write_step);puts("PASS actual large FIT: erase complete 113152 KiB before attach, write fit, recreate overlay, fresh attach");
 reset_state();small=0;fw.size=0x6e80000;assert(write_ubi_itb_image(f,39,&fw)==-EBADMSG&&erase_calls==0);puts("PASS truncated large FIT rejected before erase");
 reset_state();small=0;fw.size=0x6e80000;assert(write_ubi_itb_image(t,tn,&fw)==-EBADMSG&&erase_calls==0);puts("PASS non-FIT input rejected before large erase");
 reset_state();small=0;fw.size=fn-1;assert(write_ubi_itb_image(f,fn,&fw)==-EFBIG&&erase_calls==0);puts("PASS oversized FIT rejected before erase");
 reset_state();small=0;fw.size=0x6e80000;erase_fail=1;assert(write_ubi_itb_image(f,fn,&fw)==-EIO&&writes==0&&fw_attaches==0);puts("PASS large erase error prevents attach and firmware write");
 reset_state();small=0;fw.size=0x6e80000;empty_vols=1;cold_fail=1;assert(write_ubi_itb_image(f,fn,&fw)!=0&&!attached&&fw_attaches==2);puts("PASS large FIT fresh-attach failure prevents upgrade success");
 reset_state();small=0;fw.size=0x6e80000;remove_fail=1;assert(write_ubi_itb_image(f,fn,&fw)==-EIO&&writes==0);puts("PASS existing volume removal error prevents FIT write");
 reset_state();small=0;empty_vols=fit_written=1;assert(!boot_from_ubi(&fw,false)&&read_calls==1&&!strcmp(ubi_image_vol,"fit"));puts("PASS FIT boot probes existing volume without a missing-kernel read");

 reset_state();small=0;fw.name="ubi_0";fw.size=56*1024*1024;layout_override="oray-ubi0";assert(!mtd_update_generic(&fw,u,131072,true)&&erased_bytes==56*1024*1024&&writes==1);puts("PASS upstream Oray ubi_0 full-slot erase retained for generic writes");
 reset_state();small=0;fw.name="ubi_0";fw.size=56*1024*1024;layout_override="oray-ubi0";assert(!mtd_update_ubi_image(&fw,u,un)&&erased_bytes==56*1024*1024&&writes==1&&create_conf==0);puts("PASS upstream Oray ubi_0 full-slot erase retained for trimffs UBI writes");
 reset_state();small=0;fw.name="ubi_0";fw.size=56*1024*1024;layout_override="other";assert(!mtd_update_generic(&fw,u,131072,true)&&erased_bytes==131072);puts("PASS other ubi_0 layouts retain size-limited generic erasure");
 free(f);
 free(t);free(u);return 0;
}
'''
(OUT / 'flash_paths.c').write_text(code)
subprocess.run(['gcc','-std=gnu11','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',
                '-Wno-format','-Wno-discarded-qualifiers',str(OUT/'flash_paths.c'),'-lz','-o',str(OUT/'flash_paths')],check=True)
subprocess.run([str(OUT/'flash_paths'),str(ROOT/'evidence/1.bin'),str(ROOT/'evidence/2、CT3003new.bin'),str(ROOT/'evidence/large-matched.itb')],check=True)

from pathlib import Path
import os
import tempfile
import subprocess

R = Path(os.environ['CT3003_TEST_FIXTURES']).resolve()
S = Path(__file__).resolve().parents[2] / 'uboot-mtk-20250711'
_tmp = tempfile.TemporaryDirectory(prefix='ct3003-fdt-')
T = Path(_tmp.name)
text = (S / 'board/mediatek/common/mtd_helper.c').read_text()
a = text.index('int mtd_fixup_linux_fdt(')
b = text.index('\n}', a) + 2
function = text[a:b]
pre = r'''
#include <libfdt.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <stdbool.h>
#include <errno.h>
#include <assert.h>
typedef uint32_t u32;
#define CONFIG_ENABLE_NAND_NMBM 1
#define CONFIG_NMBM_MAX_RATIO 1
#define CONFIG_NMBM_MAX_BLOCKS 256
#define PART_UBI_NAME "ubi"
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define IS_ERR_OR_NULL(x) (!(x))
struct mtd_info {uint64_t offset,size;unsigned erasesize,writesize;};
static struct mtd_info fw={0x580000,0x6e80000,0x20000,0x800};
static struct mtd_info nm={0,0x7800000,0x20000,0x800};
static int enabled=1,missing_nmbm,alloc_fail,prop_fail,commit_fail;
static struct mtd_info *get_mtd_device_nm(const char *n){return !strcmp(n,"ubi")?&fw:!strcmp(n,"nmbm0")&&!missing_nmbm?&nm:NULL;}
static void put_mtd_device(struct mtd_info *m){}
static bool mtd_firmware_layout_flag(struct mtd_info *m,const char *f){assert(!strcmp(f,"linux-nmbm-fixup"));return enabled;}
static void *test_malloc(size_t n){return alloc_fail?NULL:malloc(n);}
static int test_setprop(void *f,int n,const char *p,const void *d,int l){return prop_fail?-FDT_ERR_NOSPACE:fdt_setprop(f,n,p,d,l);}
static int fdt_increase_size(void *f,int n){return commit_fail?-FDT_ERR_NOSPACE:fdt_open_into(f,f,fdt_totalsize(f)+n);}
#define malloc test_malloc
#define fdt_setprop test_setprop
'''
post = r'''
#undef malloc
#undef fdt_setprop
static void *load(const char *p){FILE *h=fopen(p,"rb");assert(h);void*b=calloc(1,1048576);assert(fread(b,1,1048576,h)>0);fclose(h);assert(!fdt_check_header(b));return b;}
static void save(const char*p,void*b){FILE*h=fopen(p,"wb");assert(h);assert(fwrite(b,1,fdt_totalsize(b),h)==fdt_totalsize(b));fclose(h);}
static void same_error(void*b,int want){int n=fdt_totalsize(b);void*c=malloc(n);memcpy(c,b,n);assert(mtd_fixup_linux_fdt(b)==want);assert(!memcmp(c,b,n));free(c);}
static void grow(void*b){assert(!fdt_open_into(b,b,65536));}
static int flash(void*b){return fdt_node_offset_by_compatible(b,-1,"spi-nand");}
static int ubi_node(void*b){int p=fdt_subnode_offset(b,flash(b),"partitions");return fdt_subnode_offset(b,p,"partition@580000");}
static void reset(void){enabled=1;missing_nmbm=alloc_fail=prop_fail=commit_fail=0;nm.size=0x7800000;nm.erasesize=0x20000;fw.size=0x6e80000;}
int main(int argc,char **argv){
 void*b=load(argv[1]);assert(!mtd_fixup_linux_fdt(b));int f=flash(b),len;const fdt32_t*r=fdt_getprop(b,ubi_node(b),"reg",&len);assert(r&&len==8&&fdt32_to_cpu(r[0])==0x580000&&fdt32_to_cpu(r[1])==0x6e80000);assert(fdt_getprop(b,f,"mediatek,nmbm",&len)&&len==0);r=fdt_getprop(b,f,"mediatek,bmt-max-reserved-blocks",&len);assert(r&&fdt32_to_cpu(*r)==256);save(argv[4],b);puts("PASS actual matched 25.12.2 FDT: NMBM enabled, 113152 KiB UBI, reference reservation parameters");
 same_error(b,0);free(b);puts("PASS FDT fixup is idempotent");
 reset();enabled=0;b=load(argv[1]);same_error(b,0);free(b);puts("PASS small layout leaves the big-layout kernel FDT untouched");
 reset();b=load(argv[2]);same_error(b,0);free(b);b=load(argv[3]);same_error(b,0);free(b);puts("PASS actual stock Linux 5.4 and stock sysupgrade Linux 5.15 FDTs untouched");
 reset();b=load(argv[1]);grow(b);assert(!fdt_setprop_string(b,0,"compatible","other,board"));same_error(b,0);free(b);puts("PASS other boards remain untouched");
 reset();b=load(argv[1]);grow(b);fdt32_t v[2]={cpu_to_fdt32(0x600000),cpu_to_fdt32(0x7a80000)};assert(!fdt_setprop_inplace(b,ubi_node(b),"reg",v,8));same_error(b,-EINVAL);free(b);puts("PASS unexpected partition offset rejected without FDT mutation");
 reset();b=load(argv[1]);grow(b);v[0]=cpu_to_fdt32(0x580000);v[1]=cpu_to_fdt32(0x7000000);assert(!fdt_setprop_inplace(b,ubi_node(b),"reg",v,8));same_error(b,-EINVAL);free(b);puts("PASS unexpected UBI size rejected without FDT mutation");
 reset();b=load(argv[1]);grow(b);int p=fdt_subnode_offset(b,flash(b),"partitions");assert(!fdt_setprop_u32(b,p,"#size-cells",2));same_error(b,-EINVAL);free(b);puts("PASS incompatible partition cells rejected");
 reset();b=load(argv[1]);grow(b);assert(!fdt_setprop(b,flash(b),"mediatek,bmt-v2",NULL,0));same_error(b,-EINVAL);free(b);puts("PASS conflicting NAND mapping rejected");
 reset();b=load(argv[1]);grow(b);int x=fdt_add_subnode(b,0,"another-nand");assert(x>=0);assert(!fdt_setprop_string(b,x,"compatible","spi-nand"));same_error(b,-EINVAL);free(b);puts("PASS ambiguous multiple NAND devices rejected");
 reset();b=load(argv[1]);grow(b);p=fdt_subnode_offset(b,flash(b),"partitions");assert(fdt_add_subnode(b,p,"unexpected-partition")>=0);same_error(b,-EINVAL);free(b);puts("PASS extra partitions rejected");
 reset();missing_nmbm=1;b=load(argv[1]);same_error(b,-ENODEV);free(b);reset();nm.size=0x7000000;b=load(argv[1]);same_error(b,-EINVAL);free(b);puts("PASS missing NMBM and insufficient logical capacity rejected");
 reset();alloc_fail=1;b=load(argv[1]);same_error(b,-ENOMEM);free(b);puts("PASS allocation failure leaves original FDT intact");
 reset();prop_fail=1;b=load(argv[1]);same_error(b,-FDT_ERR_NOSPACE);free(b);puts("PASS property-write failure leaves original FDT intact");
 reset();commit_fail=1;b=load(argv[1]);same_error(b,-FDT_ERR_NOSPACE);free(b);puts("PASS FDT commit failure leaves original FDT intact");
 return 0;
}
'''
(T / 'ct3003_fdt.c').write_text(pre + function + '\n' + post)
L = S / 'scripts/dtc/libfdt'
files = ['fdt.c', 'fdt_ro.c', 'fdt_rw.c', 'fdt_wip.c', 'fdt_sw.c', 'fdt_strerror.c', 'fdt_empty_tree.c']
subprocess.run(['gcc','-std=gnu11','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',
                '-I'+str(L),str(T/'ct3003_fdt.c')] + [str(L/p) for p in files] +
               ['-o',str(T/'ct3003_fdt')],check=True)
subprocess.run([str(T/'ct3003_fdt'),str(R/'kernel-1.dtb'),str(R/'stock-kernel-dtb-0x32d588.bin'),
                str(R/'sysupgrade-kernel-dtb-0x4fb1cc.bin'),str(T/'kernel-fix4.dtb')],check=True)

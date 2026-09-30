"""Actual C UBI writer with a NAND model tracking programming of erased pages.

The model represents the ECC hazard of programming 0xff, not a physical chip.
"""
from pathlib import Path
import os
import tempfile
import re
import subprocess

ROOT = Path(os.environ['CT3003_TEST_FIXTURES']).resolve()
SRC = Path(__file__).resolve().parents[2] / 'uboot-mtk-20250711'
_tmp = tempfile.TemporaryDirectory(prefix='ct3003-host-')
OUT = Path(_tmp.name)

def function(text, name):
    m = re.search(r'^(?:static )?(?:int|bool|void|size_t) ' + name + r'\(', text, re.M)
    assert m, name
    end = text.index('\n}', m.start()) + 2
    return text[m.start():end] + '\n'

mtd = (SRC / 'board/mediatek/common/mtd_helper.c').read_text()
upgrade = (SRC / 'board/mediatek/common/upgrade_helper.c').read_text()
code = r'''
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <assert.h>
#include <errno.h>
#include <zlib.h>
typedef uint8_t u8;
typedef uint32_t u32;
typedef unsigned long long u64;
typedef unsigned long ulong;
#define cprintln(level,...) printf(__VA_ARGS__)
#define ALIGN(x,a) (((x)+(a)-1)&~((a)-1))
#define MTD_OPS_AUTO_OOB 1
#define FLASH_SIZE 33554432
#define PAGE_SIZE 2048
#define BLOCK_SIZE 131072
struct mtd_info {const char*name;u64 offset,size;u32 writesize,writesize_mask,erasesize,erasesize_mask;};
struct mtd_oob_ops {int mode;void*datbuf;size_t len,retlen;};
static struct mtd_info fw={"ubi",0x580000,FLASH_SIZE,PAGE_SIZE,PAGE_SIZE-1,BLOCK_SIZE,BLOCK_SIZE-1};
static u8 *flash,*programmed,*ecc_bad;
static size_t page_programs;
static int write_error,short_write,corrupt_tail;
static int mtd_block_isbad(struct mtd_info*m,u64 a){return 0;}
static int mtd_write_oob(struct mtd_info*m,u64 a,struct mtd_oob_ops*o){
 assert(o->mode==MTD_OPS_AUTO_OOB&&o->len&&a%PAGE_SIZE==0&&o->len%PAGE_SIZE==0&&a+o->len<=m->size);
 if(write_error)return -EIO;
 if(short_write){o->retlen=o->len-PAGE_SIZE;return 0;}
 for(size_t j=0;j<o->len;j+=PAGE_SIZE){size_t p=(a+j)/PAGE_SIZE;if(programmed[p])ecc_bad[p]=1;programmed[p]=1;page_programs++;for(size_t k=0;k<PAGE_SIZE;k++)flash[a+j+k]&=((u8*)o->datbuf)[j+k];}
 o->retlen=o->len;
 if(corrupt_tail)flash[a+o->len]=0;
 return 0;
}
static int mtd_read_oob(struct mtd_info*m,u64 a,struct mtd_oob_ops*o){
 assert(a+o->len<=m->size);o->retlen=o->len;memcpy(o->datbuf,flash+a,o->len);
 for(size_t p=a/PAGE_SIZE;p<(a+o->len+PAGE_SIZE-1)/PAGE_SIZE;p++)if(ecc_bad[p])return -EBADMSG;
 return 0;
}
static void erase_model(void){memset(flash,0xff,FLASH_SIZE);memset(programmed,0,FLASH_SIZE/PAGE_SIZE);memset(ecc_bad,0,FLASH_SIZE/PAGE_SIZE);page_programs=0;write_error=short_write=corrupt_tail=0;}
static void *load(const char*p,size_t*n){FILE*f=fopen(p,"rb");assert(f);fseek(f,0,SEEK_END);*n=ftell(f);rewind(f);void*b=malloc(*n);assert(fread(b,1,*n,f)==*n);fclose(f);return b;}
static u32 get_be32(const u8*p){return ((u32)p[0]<<24)|((u32)p[1]<<16)|((u32)p[2]<<8)|p[3];}
'''
code += function(upgrade, 'check_data_size')
code += function(upgrade, 'verify_data')
code += function(mtd, 'mtd_validate_block')
code += function(mtd, 'mtd_ubi_drop_ffs')
code += function(mtd, 'mtd_write_skip_bad_common')
code += function(mtd, 'mtd_write_skip_bad')
code += r'''
int main(int argc,char**argv){
 size_t n;u8*image=load(argv[1],&n);assert(n==FLASH_SIZE);flash=malloc(n);programmed=malloc(n/PAGE_SIZE);ecc_bad=malloc(n/PAGE_SIZE);assert(flash&&programmed&&ecc_bad);
 size_t progress;
 erase_model();assert(!mtd_write_skip_bad(&fw,0,n,n,&progress,image,true)&&progress==n);assert(page_programs==n/PAGE_SIZE);assert(!memcmp(flash,image,n));
 u8 page[PAGE_SIZE];memset(page,0xa5,sizeof(page));struct mtd_oob_ops io={MTD_OPS_AUTO_OOB,page,sizeof(page),0};
 assert(programmed[209*64+1]);assert(!mtd_write_oob(&fw,209*BLOCK_SIZE+PAGE_SIZE,&io));assert(mtd_read_oob(&fw,209*BLOCK_SIZE+PAGE_SIZE,&io)==-EBADMSG);
 puts("PASS NAND model reproduces old write: byte verification passes but later programming PEB 209 fails ECC");
 erase_model();assert(!mtd_write_skip_bad_common(&fw,0,n,n,&progress,image,true,true)&&progress==n);assert(!memcmp(flash,image,n));
 size_t tails=0,expected_programs=0;
 for(size_t b=0;b<256;b++){size_t end=BLOCK_SIZE;while(end&&image[b*BLOCK_SIZE+end-1]==0xff)end--;size_t pages=(end+PAGE_SIZE-1)/PAGE_SIZE;expected_programs+=pages;for(size_t p=pages;p<64;p++){assert(!programmed[b*64+p]);tails++;}}
 assert(page_programs==expected_programs&&tails>0);assert(!programmed[96*64+1]&&!programmed[209*64+1]);
 printf("PASS supplied 32MiB image: all bytes match, positions preserved, %zu trailing blank pages remain unprogrammed\n",tails);
 const u8*table=NULL;
 for(size_t b=0;b<256;b++){const u8*p=image+b*BLOCK_SIZE;if(!memcmp(p+PAGE_SIZE,"UBI!",4)&&get_be32(p+PAGE_SIZE+8)==0x7fffefff){table=p+4096;break;}}
 assert(table&&get_be32(table+172)==105&&!memcmp(table+172+16,"rootfs",6));
 assert((crc32(0,table+172,168)^0xffffffffU)==get_be32(table+172+168));
 io.datbuf=(void*)table;io.len=22528;assert(!mtd_write_oob(&fw,209*BLOCK_SIZE+4096,&io));u8*readback=malloc(io.len);io.datbuf=readback;assert(!mtd_read_oob(&fw,209*BLOCK_SIZE+4096,&io));assert(!memcmp(readback,table,io.len));assert((crc32(0,readback+172,168)^0xffffffffU)==get_be32(readback+172+168));
 io.datbuf=page;io.len=PAGE_SIZE;assert(!mtd_write_oob(&fw,96*BLOCK_SIZE+PAGE_SIZE,&io));assert(!mtd_read_oob(&fw,96*BLOCK_SIZE+PAGE_SIZE,&io));
 puts("PASS formerly free PEBs 96/209 can accept new UBI metadata; rootfs record CRC remains valid in NAND model");
 erase_model();corrupt_tail=1;assert(mtd_write_skip_bad_common(&fw,0,BLOCK_SIZE,n,&progress,image,true,true)==-EBADMSG);puts("PASS verification includes skipped blank tail and detects unexpected data there");
 erase_model();write_error=1;assert(mtd_write_skip_bad_common(&fw,0,n,n,&progress,image,true,true)==-EIO&&progress==0);short_write=1;write_error=0;assert(mtd_write_skip_bad_common(&fw,0,n,n,&progress,image,true,true)==-EIO&&progress==0);puts("PASS write and short-write failures abort without false progress");
 erase_model();assert(mtd_write_skip_bad_common(&fw,1,n-1,n,&progress,image,true,true)==-EINVAL&&page_programs==0);assert(mtd_write_skip_bad_common(&fw,0,n-1,n,&progress,image,true,true)==-EINVAL&&page_programs==0);puts("PASS unaligned UBI input rejected before programming");
 erase_model();u8*empty=malloc(BLOCK_SIZE);memset(empty,0xff,BLOCK_SIZE);assert(!mtd_write_skip_bad_common(&fw,0,BLOCK_SIZE,n,&progress,empty,true,true)&&progress==BLOCK_SIZE&&page_programs==0);puts("PASS wholly blank eraseblock advances input without any NAND page program");free(empty);
 free(readback);free(image);free(flash);free(programmed);free(ecc_bad);return 0;
}
'''
(OUT / 'ubi_trimffs.c').write_text(code)
subprocess.run(['gcc','-std=gnu11','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',
                '-Wno-format',str(OUT/'ubi_trimffs.c'),'-lz','-o',str(OUT/'ubi_trimffs')],check=True)
subprocess.run([str(OUT/'ubi_trimffs'),str(ROOT/'evidence/2\u3001CT3003new.bin')],check=True)

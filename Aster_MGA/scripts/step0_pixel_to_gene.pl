#!/usr/bin/perl
# Step 0: convert the box coordinates read from the dot plot (pixels, or 0 / 1
# for the chromosome start / end) into gene-index coordinates.
#
# Usage:
#   perl step0_pixel_to_gene.pl REF.lens OTHER.lens REGIONS_PIXEL.txt OUT.correspondence.txt
# Example:
#   perl scripts/step0_pixel_to_gene.pl bed/Elu.lens bed/Ddev.lens \
#        regions/Elu_Ddev.regions_pixel.txt regions/Elu_Ddev.correspondence.txt
#
# Input region format : A3:Elu1:0-322:Ddev2:398-1
# Output region format: A3:Elu1:0-1675:Ddev2:763-2232
use strict;
die "Usage: perl $0 REF.lens OTHER.lens REGIONS_PIXEL.txt OUT.correspondence.txt\n" if @ARGV < 4;
#my $infile = "test_o.txt";#gene pair
my $lens1file = $ARGV[0];#chromosome lengths of species 1
open(LEN1,$lens1file) or die "can not open in file $lens1file due to $!.\n";

my $lens2file = $ARGV[1];
open(LEN2,$lens2file) or die "can not open in file $lens2file due to $!.\n";

my $position = $ARGV[2];#box coordinates
open(POS,$position) or die "can not open in file $position due to $!.\n";

my $outfile = $ARGV[3];
open(OUT,">",$outfile) or die "can not open out file $outfile due to $!.\n";
#######   parameters #######
my $pix_start_1=200;#Start pixel
my $pix_start_2=200;#Start pixel
my $end_add =0;
############################
my %hash_lens1;
my %hash_pix1;
my %hash_pix_start1;
my $temp;
my $nu;
while(<LEN1>)
{
	$_ =~ s/[\n\r]//g;
	my @array = split(/\s+/, $_);
    $hash_lens1{$array[0]}=$array[1];
#print "$array[2]\n";
#print "$array[1]\n";
#####
    $nu++;
    if($nu==1){$hash_pix_start1{$array[0]}=$pix_start_1;}
    else{$hash_pix_start1{$array[0]}=$temp;}
    $temp=$array[2];
#####
    my $pix_length=$array[2]-$hash_pix_start1{$array[0]};
    $hash_pix1{$array[0]}=$pix_length;
}
#total length
close LEN1;

my %hash_lens2;
my %hash_pix2;
my %hash_pix_start2;
my $tmp;
my $num;
if($lens1file eq $lens2file)
{
    %hash_lens2=%hash_lens1;
    %hash_pix2=%hash_pix1;
    %hash_pix_start2=%hash_pix_start1;
}else
{
    while(<LEN2>)
    {
        $_ =~ s/[\n\r]//g;
        my @array = split(/\s+/, $_);
        $hash_lens2{$array[0]}=$array[1];
        #print "$array[2]\n";
        #print "$array[1]\n";
#####
        $num++;
        if($num==1){$hash_pix_start2{$array[0]}=$pix_start_2;}
        else{$hash_pix_start2{$array[0]}=$tmp;}
        $tmp=$array[2];
#####
        my $pix_length=$array[2]-$hash_pix_start2{$array[0]};
        $hash_pix2{$array[0]}=$pix_length;
    }

}

#total length
close LEN2;


my $chr_length;#total length of a single chromosome
my $chr_vir_len;
my $start;
my $end;

my $temp_a=1;
my $temp_b=1;
my $item_a;
while(<POS>)
{
    $temp_a=();
    $num=0;
    $_ =~s/[\n\r]//g;
    my @array = split(/\s+/,$_);
    for(my $i=0;$i<$#array+1;$i++)
    {
#        print "$i\n";
        my @arr = split(/:/,$array[$i]);#A:Pp08:461-3227:Vv3:0-1104
        if($arr[0]!~/A\d$/){ print "\n\n\nWarning:\n$array[$i]\n$arr[0] is wrong!\tplease check your position file...\n";exit;}
        if(!exists $hash_lens1{$arr[1]}){ print "\n\n\nWarning:\n$array[$i]\n$arr[1] is wrong!\tplease check your file...\n";exit;}
        $num++;
###########   check format   ############
        if($num == 1){$temp_a=$arr[1];}
        $item_a = $arr[1];
#print "$temp_a\t$item_a\n";
        if($temp_a ne $item_a)
        {
            print " \n\n\nWarning:\nlast:\t$array[$i-1]\nnow:\t$array[$i]\na_last: $temp_a\ta_now: $item_a\n$item_a is wrong!\tplease check your position file...\n";exit;	
        }
        $temp_a=$arr[1];
#########################################
        $chr_length=$hash_lens1{$arr[1]};#
        if($arr[2]=~/[a-zA-Z]/){ print "\n\n\nWarning:\n$array[$i]\n$arr[2] is wrong!\tplease check your file...\n";exit;}
        my @ar_a = split(/\-/,$arr[2]);#
        $chr_vir_len=$hash_pix1{$arr[1]};#
        if($ar_a[0] == 0){$start = 0;}
        elsif($ar_a[0]=~/0\.\d/){$start = int($ar_a[0]*$chr_length);}
        elsif($ar_a[0]=~/\d\/\d$/){$start = int(eval($ar_a[0])*$chr_length);}
        else
        {   
            if($ar_a[0]=~/\./ || $ar_a[0]=~/\// || $ar_a[0]=~/\\/){print "\n\n\nWarning:\n$ar_a[0] is wrong!\tplease check your position file...\n";exit;}
            my $vir_seg_a =$ar_a[0]-$hash_pix_start1{$arr[1]};#length of segment 0-a
            if($vir_seg_a >= $chr_vir_len){print "\n\n\nWarning:\n$array[$i]\n$arr[2]\n$ar_a[0]\tthere are promble!...\nvir_seg/chr_vir_len>=1\n";exit;}
            $start = int(($vir_seg_a/$chr_vir_len)*$chr_length);
        }
        if($ar_a[1] == 1){$end = $chr_length+$end_add;}
        elsif($ar_a[1]=~/0\.\d/){$end = int($ar_a[1]*$chr_length+0.5);}
        elsif($ar_a[1]=~/\d\/\d$/){$end = int(eval($ar_a[1])*$chr_length+0.5);}
        else
        {
            if($ar_a[1]=~/\./ || $ar_a[1]=~/\// || $ar_a[1]=~/\\/){print "\n\n\nWarning:\n$ar_a[1] is wrong!\tplease check your position file...\n";exit;}
            my $vir_seg_a =$ar_a[1]-$hash_pix_start1{$arr[1]};#length of segment 0-a
            if($vir_seg_a > $chr_vir_len){print "\n\n\nWarning:\n$array[$i]\n$arr[2]\n$ar_a[1]\tthere are promble!...\nvir_seg/chr_vir_len>1\n";exit;}
            if($vir_seg_a == $chr_vir_len)
            {
                $end =$chr_length + $end_add;
            }else
            {
                $end = int(($vir_seg_a/$chr_vir_len)*$chr_length+0.5);
            }
        }
        my $postion_a="$start-$end";
        if($start<0 || $end<0 || $start >= $end){print "\n\n\nWarning:\n$array[$i]\n$arr[0]:$arr[1]:$arr[2] has something wrong!\npostion_a:$start-$end\tplease check your position file...\n";exit;}
#second half (species 2)
        if(!exists $hash_lens2{$arr[3]}){ print "\n\n\nWarning:\n$array[$i]\n$arr[3] is wrong!\tplease check your file...\n";exit;}
        $chr_length=$hash_lens2{$arr[3]};#
#        print "$arr[3]\n";
        if($arr[4]=~/[a-zA-Z]/){ print "\n\n\nWarning:\n$array[$i]\n$arr[4] is wrong!\tplease check your file...\n";exit;}
        my @ar_b = split(/\-/,$arr[4]);#
        $chr_vir_len=$hash_pix2{$arr[3]};#
#print "($ar_b[0]\/$chr_vir_len)*$chr_length)\n";
        if($ar_b[0] == 0){$start = 0;}
        elsif($ar_b[0]=~/0\.\d/){$start = int($ar_b[0]*$chr_length);}
        elsif($ar_b[0]=~/\d\/\d$/){$start = int(eval($ar_b[0])*$chr_length);}
        else
        {
            if($ar_b[0]=~/\./ || $ar_b[0]=~/\// || $ar_b[0]=~/\\/){print "\n\n\nWarning:\n$ar_b[0] is wrong!\tplease check your position file...\n";exit;}
            my $vir_seg_b =$ar_b[0]-$hash_pix_start2{$arr[3]};#length of segment 0-b
            if($vir_seg_b >= $chr_vir_len){print "\n\n\nWarning:\n$array[$i]\n$arr[4]\n$ar_b[0]\tthere are promble!...\nvir_seg/chr_vir_len>=1\n";exit;}
            $start = int(($vir_seg_b/$chr_vir_len)*$chr_length);
        }
        if($ar_b[1] == 1){$end = $chr_length+$end_add;}
        elsif($ar_b[1]=~/0\.\d/){$end = int($ar_b[1]*$chr_length+0.5);}
        elsif($ar_b[1]=~/\d\/\d$/){$end = int(eval($ar_b[1])*$chr_length+0.5);}
        else
        {
            if($ar_b[1]=~/\./ || $ar_b[1]=~/\// || $ar_b[1]=~/\\/){print "\n\n\nWarning:\n$ar_b[1] is wrong!\tplease check your position file...\n";exit;}
            my $vir_seg_b =$ar_b[1]-$hash_pix_start2{$arr[3]};#length of segment 0-b
            if($vir_seg_b > $chr_vir_len){print "\n\n\nWarning:\n$array[$i]\n$arr[4]\n$ar_b[1]\tthere are promble!...\nvir_seg/chr_vir_len>1\n";exit;}
            if($vir_seg_b == $chr_vir_len)
            {
                $end =$chr_length + $end_add;
            }else
            {
                $end = int(($vir_seg_b/$chr_vir_len)*$chr_length+0.5);
            }
        }
        my $postion_b="$start-$end";
        if($start<0 || $end<0 || $start >= $end){print "\n\n\nWarning:\n$array[$i]\n$arr[3]:$arr[4] has something wrong!\npostion_b:$start-$end\tplease check your position file...\n";exit;}
########## add zero on chr numbers  ######
 #       $arr[1]=~s/^(\D+)(\d)$/${1}0${2}/;
 #       $arr[3]=~s/^(\D+)(\d)$/${1}0${2}/;
##########################################
        if($i==$#array){print OUT "$arr[0]:$arr[1]:$postion_a:$arr[3]:$postion_b\n";}
        else{print OUT "$arr[0]:$arr[1]:$postion_a:$arr[3]:$postion_b\t";}
        print "$arr[0]:$arr[1]:$postion_a:$arr[3]:$postion_b\n";
    }
}
close POS;
close OUT;
#Made in china
#Writed by eXps
#Version:3.1

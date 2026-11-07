#!/usr/bin/perl
# Ks dot plot: draws the collinear blocks of a species pair as dots and labels every
# block with its median Ks (red if the median Ks is below the cutoff, otherwise black).
# Normally called by run_ks_dot.py.
#
# Usage:
#   perl ks_dotplot.pl QUERYCHR SBJCTCHR QUERYGFF SBJCTGFF BLOCK POS_OR_ORDER \
#        QUERYINITIAL SBJCTINITIAL PVALUE MINLENGTH MAXLENGTH KS_CUTOFF QUERYNAME SBJCTNAME
#
#   QUERYCHR, SBJCTCHR  chromosome numbers joined by "_", e.g. 1_2_3_4_5
#   QUERYGFF, SBJCTGFF  <species>.new.gff
#   BLOCK               *_block_rr.latest.txt (blocks with Ks and rank inserted, see run_ks_dot.py)
#   POS_OR_ORDER        "order" (position = gene order) or "pos" (position = bp)
#   PVALUE              draw only blocks with p-value below this
#   MINLENGTH, MAXLENGTH  draw only blocks with this many gene pairs
#   KS_CUTOFF           median Ks below this value: label drawn in red
#   QUERYNAME, SBJCTNAME  full species names used as axis titles
# Output: <sbjct>_<query>.Ksdotplot.png (the two species names are in this order,
#         taken from the second and first part of the block file name)
#
# Environment: KS_DOTPLOT_FONT = path of a TrueType font
#              (default /usr/share/fonts/dejavu/DejaVuSans.ttf)
# Needs the Perl modules GD and GD::Text::Align.

use strict;
use GD;
use GD::Text::Align;

my $FONT = $ENV{KS_DOTPLOT_FONT} || '/usr/share/fonts/dejavu/DejaVuSans.ttf';
die "Usage: see the header of $0\n" if @ARGV < 14;

my @querychr = split(/_/, $ARGV[0]);
my @sbjctchr = split(/_/, $ARGV[1]);
my $ks_flag= $ARGV[11];

my $queryspecies = $ARGV[6];
my $sbjctspecies = $ARGV[7];

#my $figure_file = "Oryza sativa".$ARGV[0].".v."."Triticum urartu".$ARGV[1].".colinearscan2dotplot.png";
my @name=split(/_/, $ARGV[4]);
my $figure_file = "$name[1]\_$name[0].Ksdotplot.png";
#my $chrolenfile1 = $ARGV[2];
#my %sbjctchr2len;
#input_chro_len1($chrolenfile1);

#foreach my $chr(sort(keys(%sbjctchr2len)))
#{
#   print "$chr $sbjctchr2len{$chr} \n";
#}

###### parameters for significant hits, for filtering repeats
my $EVALUE = 1e-5;
my $SCORE  = 200;
my $HITNUM = 5;
my $REPNUM = 20;

###### parameters for input files
my $querygenegff = $ARGV[2]; ### for gne positions
open(QGFF, $querygenegff) or die "cannot open $querygenegff due to $!\n";

my %querygene2pos;
my %querygene2order;
my %querygene2chr;
my %querychr2plen;
my %querychr2olen;
my $geneNumOnAchr;
my $lastchr = "";
while(<QGFF>)
{chomp;
  my @a = split(/\t/, $_);
  if($a[0] eq $lastchr)
  {
    $geneNumOnAchr ++;
	#print"###\n";
  }
  else
  {
    $geneNumOnAchr = 1;
  }
  $querygene2order{$a[5]}=$geneNumOnAchr;#gene order
  $querygene2pos{$a[5]} = $a[6];
  my $chr = $a[0];#chr
  $querygene2chr{$a[5]} = $chr;


  if($querychr2olen{$a[0]} !~ /^\d/)
  {
     $querychr2olen{$a[0]} = $geneNumOnAchr;
	 #print"$a[0]###$querychr2olen{$a[0]}\n";
  }
  elsif($querychr2olen{$a[0]} < $geneNumOnAchr)
  {
     $querychr2olen{$a[0]} = $geneNumOnAchr;
  }

  if($querychr2plen{$a[0]} !~ /^\d/)
  {
     $querychr2plen{$a[0]} = $a[6];#
  }
  elsif($querychr2plen{$a[0]} < $a[6])#
  {
     $querychr2plen{$a[0]} = $a[6];#
  }
  $lastchr = $chr;
}

my $sbjctgenegff = $ARGV[3]; ### for gne positions
open(SGFF, $sbjctgenegff) or die "cannot open $sbjctgenegff due to $!\n";

my %sbjctgene2pos;
my %sbjctgene2order;
my %sbjctgene2chr;
my %sbjctchr2plen;
my %sbjctchr2olen;
   $geneNumOnAchr = 0;
   $lastchr = "";
while(<SGFF>)
{chomp;
  my @a = split(/\t/, $_);
  if($a[0] eq $lastchr)
  {
    $geneNumOnAchr ++;
  }
  else
  {
    $geneNumOnAchr = 1;
  }
  $sbjctgene2order{$a[5]}=$geneNumOnAchr;
  $sbjctgene2pos{$a[5]} = $a[6];
  my $chr = $a[0];
  $sbjctgene2chr{$a[5]} = $chr;


  if($sbjctchr2olen{$a[0]} !~ /^\d/)
  {
     $sbjctchr2olen{$a[0]} = $geneNumOnAchr;
  }
  elsif($sbjctchr2olen{$a[0]} < $geneNumOnAchr)
  {
     $sbjctchr2olen{$a[0]} = $geneNumOnAchr;
  }

  if($sbjctchr2plen{$a[0]} !~ /^\d/)
  {
     $sbjctchr2plen{$a[0]} = $a[6];
  }
  elsif($sbjctchr2plen{$a[0]} < $a[6])#Chr order
  {
     $sbjctchr2plen{$a[0]} = $a[6];
  }
  $lastchr = $chr;
}
#foreach my $chr(sort(keys(%querychr2len)))
#{
#  print "$chr $querychr2len{$chr}\n";
#}

###### parameters of the figures
my $cell_width = 2;
my $cell_height= $cell_width;
my $frame_width = 3000;############################
my $frame_height= 3000;############################

my $left_curb = 200;
my $top_curb  = 200;

open(FIG, ">".$figure_file) or die "cannot open $figure_file due to $!\n";


my @querychrlen = ();
my %querychr2order;
my @sbjctchrlen = ();
my %sbjctchr2order;
if($ARGV[5] eq "order")
{
   for(my $i=0; $i<=$#querychr; $i++)
   {
      my $chr = $querychr[$i];
	  #print "$chr\n";
      $querychrlen[$#querychrlen+1] = $querychr2olen{$chr};
	  #print "$#querychrlen\n";(the problem is in the array @querychrlen)
      $querychr2order{$chr} = $#querychrlen;
   }
      #print "$#querychrlen\n";
   for(my $i=0; $i<=$#sbjctchr; $i++)
   {
      my $chr = $sbjctchr[$i];
      $sbjctchrlen[$#sbjctchrlen+1] = $sbjctchr2olen{$chr};
      $sbjctchr2order{$chr} = $#sbjctchrlen;
   }
}
elsif($ARGV[5] eq "pos")
{
   for(my $i=0; $i<=$#querychr; $i++)
   {
      my $chr = $querychr[$i];
      $querychrlen[$#querychrlen+1] = $querychr2plen{$chr};

	  $querychr2order{$chr} = $#querychrlen;
   }

   for(my $i=0; $i<=$#sbjctchr; $i++)
   {
      my $chr = $sbjctchr[$i];
      $sbjctchrlen[$#sbjctchrlen+1] = $sbjctchr2plen{$chr};
      $sbjctchr2order{$chr} = $#sbjctchrlen;
   }
}
#print "$#querychrlen\n";

my ($genome1_length, $genome2_length) = (0, 0);

$genome1_length = sum_chr_len(@querychrlen);   
$genome2_length = sum_chr_len(@sbjctchrlen);
print "@querychrlen#\n@sbjctchrlen\n";
my $querychrno = $#querychrlen + 1;
my $sbjctchrno = $#sbjctchrlen + 1;

###### calculate scale ratio
my $scale_ratio1 = $genome1_length/$frame_width; ## horizontal
my $scale_ratio2 = $genome2_length/$frame_height;## vertical

###### draw the frame and the saprating lines corresponding to chromosome borders
my $img = GD::Image -> new($frame_width + 3/2*$left_curb, $frame_height + 3/2*$top_curb);
my $white = $img -> colorAllocate(255,255,255);
#$img -> transparent($white);
$img -> interlaced('true');

my $black = $img->colorAllocate(0,0,0);
my $red = $img->colorAllocate(255,0,0);
my $blue = $img->colorAllocate(0,0,255);
my $green = $img->colorAllocate(255,0,255);
my $yellow = $img->colorAllocate(250,250,200);
my $gray = $img->colorAllocate(100,100, 100);
my $grey = $img->colorAllocate(151,151, 151);
print "outerframe: $frame_width, $frame_height\n";

$img -> rectangle($left_curb, $top_curb, $frame_width + $left_curb, $frame_height + $top_curb, $black);
$img -> rectangle($left_curb-1, $top_curb-1, $frame_width + $left_curb+1, $frame_height + $top_curb+1, $black);

my $align = GD::Text::Align->new($img, valign => 'center', halign => 'center', color => $black);
$align->set_font($FONT, 35);####################
my @query_chro_pos = ();
my @sbjct_chro_pos = ();

my $accumulated_length = 0;
for(my $i=0; $i<=$#querychrlen; $i++)
{
   $accumulated_length += $querychrlen[$i];
   #print "#$querychrlen[$i]#";
   my $length = int($querychrlen[$i]/$scale_ratio1);
   my $posx1 = $left_curb + int($accumulated_length/$scale_ratio1);
   $query_chro_pos[$i] = $posx1;
   my $posy1 = $top_curb;
   my $posx2 = $posx1;
   my $posy2 = $top_curb + $frame_height;

#print "x chromosome: ".$posx1." ".$posy1." ".$posx2." ".$posy2."\n";
   $img -> line($posx1, $posy1, $posx2, $posy2, $black);
   $img -> line($posx1+1, $posy1, $posx2+1, $posy2, $black);

   my $chr = $querychr[$i];
   $chr =~s/\D//g;
   $chr =~s/0(\d)$/$1/g;
   $align->set_text($chr);
   #$align->draw($posx1-int($length/2)+15, 150,0);
   $align->draw($posx1-int($length/2), 160,0);#######################
   #$img -> string(gdGiantFont, $posx1-int($length/2)-40, 50, $chr, $red);
}
my $lenth1 = int($accumulated_length/$scale_ratio1);
my $posx1 = $left_curb + int($accumulated_length/$scale_ratio1);
   my $posy1 = $top_curb;
   my $posx2 = $posx1;
   my $posy2 = $top_curb + $frame_height;

for( my $j=1;$j*($lenth1)/90<$lenth1;$j++)
{
	#$img -> line($posx1-$lenth1/90*$j,$posy1,$posx2-$lenth1/90*$j,$posy2,$grey);############################
}

=pod
=cut

$accumulated_length = 0;
for(my $i=0; $i<=$#sbjctchrlen; $i++)
{
   $accumulated_length += $sbjctchrlen[$i];
   my $length = int($sbjctchrlen[$i]/$scale_ratio2);
   my $posy1 = $top_curb + int($accumulated_length/$scale_ratio2);
   $sbjct_chro_pos[$i] = $posy1;
   my $posx1 = $left_curb;
   my $posy2 = $posy1;
   my $posx2 = $left_curb + $frame_width;

#print "y chromosome: ".$posx1." ".$posy1." ".$posx2." ".$posy2."\n";
   $img -> line($posx1, $posy1, $posx2, $posy2, $black);
   $img -> line($posx1, $posy1+1, $posx2, $posy2+1, $black);
   my $chr = $sbjctchr[$i];
   $chr =~s/\D//g;
   $chr =~s/0(\d)$/$1/g;
   $align->set_text($chr);
   $align->draw(150, $posy1-int($length/2), 0);########################
   #$img -> string(gdGiantFont, 40, $posy1-int($length/2)-40, $chr, $red);
}
my $lenth2 = int($accumulated_length/$scale_ratio2);
my $posx1 = $left_curb;
   my $posy1 = $top_curb + int($accumulated_length/$scale_ratio2);
   my $posx2 = $left_curb + $frame_width;
   my $posy2 = $posy1;

for( my $m=1;$m*($lenth2)/90<$lenth2;$m++)
{
	#$img -> line($posx1,$posy1-$lenth2/90*$m,$posx2,$posy2-$lenth2/90*$m,$grey);############################
}
=pod
=cut
$align->set_font($FONT,90);
$align->set_text("$ARGV[12]");
$align->draw($frame_width/2 + $left_curb,65,0);
$align->set_text("$ARGV[13]");
$align->draw(65,$frame_height/2 + $top_curb,1.57);

print "accumulated chro length is $accumulated_length\n";

open(IN, $ARGV[4]) or die "cannot open infile due to $!.\n";

my $isoutput = 0;
my $LENGTH = $ARGV[9];
my $LENGTH2 = $ARGV[10];
my $PVALUE = $ARGV[8];
my $lastquery = "";
my $hitnum = 0;
my $color = $black;
my $number = 0;
my @AllgeneInABlock = ();
my $proid1 = "";
my $proid2 = "";
my $wcd;
while(<IN>)
{
#print $_;
   $_ =~ s/[\n\r]//g;

   my @a = split(/\s+/, $_);
   if($a[0] eq ""){next;}
   if($a[0] =~ /^\+/){next;}
    
   if($a[0] eq "the")
   {
      $isoutput = 1;
     $wcd=$a[4];
      if($a[4] < $LENGTH || $a[4] > $LENGTH2){$isoutput = 0; next;}
   }   
   if($isoutput eq 0){next;}

   if($a[0] =~ /^>LOCALE/)
   {
      if($a[3] < $PVALUE)
      {
	 my @list = ();
	 my $minx = 1000000000000000; my $miny = 1000000000000000;
	 my $maxx = 0; my $maxy = 0;
	 for(my $i=0; $i<=$#AllgeneInABlock; $i++)
	 {
	    my @temparr = split(/\s+/, $AllgeneInABlock[$i]);
	    my $tempx = $temparr[0];
	    my $tempy = $temparr[1];
	    my $sortnumber = $temparr[3];
	    if($tempx<$minx){$minx=$tempx;}
	    if($tempy<$miny){$miny=$tempy;}
	    if($tempx>$maxx){$maxx=$tempx;}
	    if($tempy>$maxy){$maxy=$tempy;}
	    if($temparr[2] >= 0 and $temparr[2] <= 2){
		    #print $temparr[2]."\n";
		    push(@list,$temparr[2]);}
	    if($temparr[3]==1){
	    $img -> filledRectangle($tempx, $tempy, $tempx+2, $tempy+2, $red);}
   	    elsif($temparr[3]==2){
	    $img -> filledRectangle($tempx, $tempy, $tempx+1, $tempy+1, $blue);}
            else{
            $img -> filledRectangle($tempx, $tempy, $tempx+1, $tempy+1, $gray);} 
	 }
	 my $mid = mid(@list);
     #print "I see $mid\t$ks_flag\n";
	 if($mid<$ks_flag){$align->set(color=>$red);}
	 else{$align->set(color=>$black);}
	 ######draw Ks
     
	 #$align->set_font('C:\WINDOWS\Fonts\TIMESBD.TTF',20);
	 if($wcd>=10)
     {
     $align->set_font($FONT,20);
     $align->set_text($mid);
     $align->draw($minx/2+$maxx/2,$maxy+15,0);
 }
     #$align->draw($minx/2+$maxx/2,$maxy+15,0);
      }      
      @AllgeneInABlock = ();
      $number = 0;
      next;
   }
   
   my $ks = 0; my $ka = 0;
   if($a[0] eq $proid1 and $a[1] eq $proid2 and $number ne 0)
   {
      $ks = $a[3];
      $ka = $a[4];
      # if($number == 0){print $proid1."\t".$proid2."\t".$_."\n";}
      $AllgeneInABlock[$number-1] .= "\t".$ks."\t".$ka;
      next;
   }

   my $id1 = $a[0];
   my $id2 = $a[2];
   $proid1 = $id1;
   $proid2 = $id2;
   
   my $querychr = $querygene2chr{$id1};
   my $sbjctchr = $sbjctgene2chr{$id2};

# only selected chromosome;
   my $is2skip1 = 1;
   for(my $i=0; $i<=$#querychr; $i++)
   {
     if($querychr eq $querychr[$i]){$is2skip1 = 0; last;}
   }
   my $is2skip2 = 1;
   for(my $i=0; $i<=$#sbjctchr; $i++)
   {
     if($sbjctchr eq $sbjctchr[$i]){$is2skip2 = 0; last;}
   }

   if($is2skip1 eq 1 || $is2skip2 eq 1){next;}


#print "query $querychr sbjct $sbjctchr\n";

   my ($posx1, $posy1, $posx2, $posy2, $selfhit1x, $selfhit1y, $selfhit2x, $selfhit2y);

   if($ARGV[5] eq "order")
   {

#print "query to order $querychr2order{$querychr}\n";
      if($querychr2order{$querychr} eq 0)
      {
         $posx1 = $left_curb + $querygene2order{$id1}/$scale_ratio1;
      }
      else
      {
         $posx1 = $query_chro_pos[$querychr2order{$querychr}-1] + $querygene2order{$id1}/$scale_ratio1;
      }

#print "sbjct to order $sbjctchr2order{$sbjctchr}\n";
      if($sbjctchr2order{$sbjctchr} eq 0)
      {
         $posy1 = $top_curb + $sbjctgene2order{$id2}/$scale_ratio2;
      }
      else
      {
         $posy1 = $sbjct_chro_pos[$sbjctchr2order{$sbjctchr}-1] +  $sbjctgene2order{$id2}/$scale_ratio2;
      }
   }
   elsif($ARGV[5] eq "pos")
   {

#print "query to order $querychr2order{$querychr}\n";
      if($querychr2order{$querychr} eq 0)
      {
         $posx1 = $left_curb + $querygene2pos{$id1}/$scale_ratio1;
      }
      else
      {
         $posx1 = $query_chro_pos[$querychr2order{$querychr}-1] + $querygene2pos{$id1}/$scale_ratio1;
      }

#print "sbjct to order $sbjctchr2order{$sbjctchr}\n";
      if($sbjctchr2order{$sbjctchr} eq 0)
      {
         $posy1 = $top_curb + $sbjctgene2pos{$id2}/$scale_ratio2;
      }
      else
      {
         $posy1 = $sbjct_chro_pos[$sbjctchr2order{$sbjctchr}-1] +  $sbjctgene2pos{$id2}/$scale_ratio2;
      }
   }

#print "posx1 $posx1 poxy1 $posy1\n";
   $AllgeneInABlock[$number] = $posx1."\t".$posy1; 
   $number ++;
}

binmode FIG;
print FIG $img -> png;

close($figure_file);


sub sum_chr_len()
{
   my @chrlen = @_;
#print "@chrlen[0..$#chrlen]\n";

   my $sumlen = $chrlen[0];
   for(my $i=1; $i<=$#chrlen; $i++)
   {
#    print "input chro len ".$chrlen[$i]."\n";
    $sumlen = $sumlen + $chrlen[$i];
   }
   return $sumlen;
}

sub mid()
{
    my @list = sort @_;
    my $count = @list;
    if( $count == 0 )
    {
        return "-2";
     }    
    
    my $mm = sprintf("%.2f",$list[int(($count-1)/2)]);
    return $mm;
}
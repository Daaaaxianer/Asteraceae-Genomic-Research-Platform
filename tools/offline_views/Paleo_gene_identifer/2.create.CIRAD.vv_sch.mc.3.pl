use strict;

my %gene2pos;

# my $tc_gff = "Nda.new.gff";
# my $Sp_gff = "Aco.new.gff";
my $tc_species_name = $ARGV[0];
my $Sp_species_name = $ARGV[1];
my $tc_gff = $tc_species_name . ".new.gff";
my $Sp_gff = $Sp_species_name . ".new.gff";


open(GG, $Sp_gff) or die "cannot open Sp gff file \n";
open(TG, $tc_gff) or die "cannot open tc gff file \n";
# my $testfile = "Nda_Aco.orthlogous.txt";
my $testfile = $tc_species_name . $Sp_species_name . ".orthlogous.txt";
open(TF,">",$testfile) or die "can not open test file $testfile due to $!.\n";
open(OUT1, ">1.txt") or die "cannot open output file due to $!.\n";

while(<GG>)#not reference genome
{
  my @arr = split(/\s+/, $_);
  $gene2pos{$arr[5]} = $arr[6];
}

my @table = ();
my $tcgenenum = 0;
my %tcgene2order;
while(<TG>)#reference genome
{
    #if($_ =~ /r/){next;}
  my @arr = split(/\s+/, $_);
  #if($arr[1] =~ /Tc00/){next;}

  $gene2pos{$arr[5]} = $arr[6];
#print $arr[1]." ".$arr[2]."\n";
  $table[$tcgenenum][0] = $arr[5];
  $table[$tcgenenum][1] = " ";
  $table[$tcgenenum][2] = " ";    ## 1:2
  $table[$tcgenenum][3] = " ";
  $table[$tcgenenum][4] = " ";   ##  1:3
  $table[$tcgenenum][5] = " ";
  $table[$tcgenenum][6] = " ";
  $tcgene2order{$arr[5]} = $tcgenenum;
  $tcgenenum ++;
}

# open(CP, "Nda_Aco.corr.txt") or die "cannot open Vv Sp correspondence file due to $!\n";
open(CP, $tc_species_name . "_" . $Sp_species_name . ".corr.txt") or die "cannot open Vv Sp correspondence file due to $!\n";
my $tc2Sp_ortho_regions = "";
while(<CP>)
{
   $_ =~ s/[\n\r]//g;
  #$_ =~s/Vv0/Vv/g;
   $tc2Sp_ortho_regions .= $_."\t";
}
print "tc2Sp orthologous regions: $tc2Sp_ortho_regions\n";

# my $blockfile = "Nda_Aco.block.rr.txt";

my $blockfile = $tc_species_name . "_" . $Sp_species_name . ".block.rr.txt";
open(IN, $blockfile) or die "cannot open $blockfile due to $!.\n";
my $colnum = 0;
my %Spgene2colnum;
while(<IN>)
{
      if($_ =~ /^[+\s]/){next;}
      if($_ =~ /^t/){my @colnum = split(/\s/, $_); $colnum = $colnum[4]; $colnum =~ s/[\n\r]//g; next;}
      if($_ =~ /^overlap/){next;}
      $_ =~ s/[\n\r]//;
      my ($id2, $pos2, $id1, $pos1, $orient) = split(/\s/, $_);
      if($Spgene2colnum{$id1} !~ /\d/){$Spgene2colnum{$id1} = $colnum;}
      elsif($Spgene2colnum{$id1}<$colnum){$Spgene2colnum{$id1} = $colnum;}
}


my @blocklines = ();
open(IN, $blockfile) or die "cannot open $blockfile due to $!.\n";

my $num = -1;
my ($id1, $id2, $pos1, $pos2, $orient);
my ($start1, $start2, $end1, $end2);
my ($startid1, $startid2, $endid1, $endid2);
my ($sp1, $sp2, $chr1, $chr2);
my %type2col = ("A1", 1, "A2", 2, "A3", 3, "A4", 4, "A5", 5, "A6", 6);
my %region2Spgene;
my $colnum = 0;
while(<IN>)
{
      if($_ =~ /^[+\s]/){next;}
      if($_ =~ /^t/){my @colnum = split(/\s/, $_); $colnum = $colnum[4]; $colnum =~ s/[\n\r]//g; $num++; next;}
    #print "+++++++++++++++++++++++".$colnum."\n";
      if($_ =~ /^overlap/){next;}

      if($_ =~ /^>/)
      {
        my @pv = split(/\s/, $_);
        $pv[3] =~ s/[\n\r]//g;

        $end1 = $gene2pos{$id1}; 
        $end2 = $gene2pos{$id2}; 
        $endid1 = $id1;
        $endid2 = $id2;
        print "$_";
    # print "###########################111111111".$end1."\n";
    # print OUT1 $endid2."\n";
        

        #######################################################################################################################################################
        if($pv[3] > 0.001 || $endid2 =~ /^Tc00/ || $colnum <= 4)
        { 
           @blocklines = ();
           $num = -1;
           next;
        }

        # print "Tc chro is $chr2 this the block: \n";
        # print "start is $startid1 $start1 end is $endid1 $end1\n";
        # print "start is $startid2 $start2 end is $endid2 $end2\n";

        my @t2g = split(/\s+/, $tc2Sp_ortho_regions);

        for(my $i=0; $i<=$#t2g; $i++)
        { 
          my ($type, $tcchr, $tcseg_start, $tcseg_end,  $Spchr, $Spseg_start, $Spseg_end) = split(/[:-]/, $t2g[$i]);
          if($tcchr !~ /$chr2/ || $Spchr !~ /$chr1/){next;}

             # print "check whether the block is the following region:\n";
             # print "TYPE: $type, GR: $Spchr, $Spseg_start, $Spseg_end TC: $tcchr, $tcseg_start, $tcseg_end\n";

             my $is2insert = 0;
             for(my $n =0; $n<=$#blocklines; $n++)
             {
                my ($id2, $pos2, $id1, $pos1, $orient) = split(/\s/, $blocklines[$n]);###################################################for rr file not right
        #print "#############".$id2." ".$pos2." ".$id1." ".$pos1." ".$orient."\n";
        
                if($region2Spgene{join("_", $Spchr, $Spseg_start, $Spseg_end, $tcchr, $tcseg_start, $tcseg_end)} =~/^\w/)
                {
                   my @Spgenes = split(/\t/, $region2Spgene{join("_", $Spchr, $Spseg_start, $Spseg_end, $tcchr, $tcseg_start, $tcseg_end)});
                   for(my $g=0; $g<=$#Spgenes; $g++)
                   {
               # print "##############".$Spgenes[$g]."\n";
                      if($id1 eq $Spgenes[$g]){print "$id1 appeared previsously\n"; $is2insert --;}
                   }
                }
                if($Spgene2colnum{$id1} > $colnum){$is2insert --;}
             }

if($colnum + $is2insert < 4){print "not inserted due to id1 has appeared previously\n";}

#print "++++++++++++++++++++++++++++++++".$chr2."\n";
      if($colnum + $is2insert >= 4 && $tcchr eq $chr2 && $Spchr eq $chr1 && min($start1, $end1) > $Spseg_start-10 && max($start1, $end1) < $Spseg_end+10)
             {
               if(($tcseg_start + $tcseg_end > 0 && min($start2, $end2) > $tcseg_start-10 && max($start2, $end2) < $tcseg_end+10) || $tcseg_start + $tcseg_end eq 0)
             {
    # print "region and column ".$t2g[$i]."\t".$type2col{$type}."\n";
  #               #############
  #               print "inserted: TYPE: $type, SI: $Spchr, $Spseg_start, $Spseg_end TU: $tcchr, $tcseg_start, $tcseg_end\n";
                 for(my $n =0; $n<=$#blocklines; $n++)
                 {
                    #print $blocklines[$n];
                    my ($id2, $pos2, $id1, $pos1, $orient) = split(/\s+/, $blocklines[$n]);##################################for rr file not right
# print TF"after inserting : $id1, $pos1, $id2, $pos2, $orient col $type $type2col{$type} $tcgene2order{$id2}\n";
                    $table[$tcgene2order{$id2}][$type2col{$type}] = $id1; 
          #print "+++++++++++++++++++++++++++++++++++".$Spchr." ".$Spseg_start." ".$Spseg_end." ".$tcchr." ".$tcseg_start." ".$tcseg_end."\n";
                    if($region2Spgene{join("_", $Spchr, $Spseg_start, $Spseg_end, $tcchr, $tcseg_start, $tcseg_end)} !~ /^\w/)
                    {
                       $region2Spgene{join("_", $Spchr, $Spseg_start, $Spseg_end, $tcchr, $tcseg_start, $tcseg_end)} = $id1;
                    }
                    else
                    {
                       $region2Spgene{join("_", $Spchr, $Spseg_start, $Spseg_end, $tcchr, $tcseg_start, $tcseg_end)} .= "\t".$id1;
                    }
                 }
             }
              else{print "not inserted due to Tu region not good\n";}
            }
            else
            {
              print "not inserted due to Si region not good\n";
            }
        }

        @blocklines = ();
        $num = -1;
     
        next;
      }
      
      $blocklines[$#blocklines+1] = $_;
    # if($_ !~ /Tc00/){print "before inserting : ".$_;}
      $_ =~ s/[\n\r]//;
      ($id2, $pos2, $id1, $pos1, $orient) = split(/\s/, $_);################################################for rr file not right
      if($#blocklines eq 0)
      {
       $sp1 = substr($id1, 0, 2);
       $sp2 = substr($id2, 0, 2);
       my @chr1 = split(/g/, $id1); 
       my @chr2 = split(/g/, $id2); #tc is chr2 with Sp as chr1

       $start1 = $gene2pos{$id1};
       $start2 = $gene2pos{$id2};
       $startid1 = $id1;
       $startid2 = $id2;
       $chr1 = $chr1[0];
       $chr2 = $chr2[0];
       
      }
}

open(TB, ">" . $tc_species_name . "_" . $Sp_species_name . ".mc.1.txt") or die "cannot open output file due to $!.\n";

#######################################################
my @lastgenes = ("", "", "", "", "", "");
my @lastpos   = (-1, -1, -1, -1, -1, -1);
for(my $i=0; $i<$tcgenenum; $i++)
{
  my @thisgenes = ();
  for(my $j=0; $j<=2; $j++)
  {
    $thisgenes[$j] = $table[$i][$j];
# print "##############################5"." ".$thisgenes[$j]." ".$lastgenes[$j]."\n";
    if($j eq 0){next;}
    if($thisgenes[$j] !~ /$Sp_species_name/){next;}

    if($lastgenes[$j] eq "")
    {
       $lastgenes[$j] = $thisgenes[$j];
       $lastpos[$j] = $i;
    }
    elsif($lastgenes[$j] =~ /^$Sp_species_name/)
    {
       if(substr($lastgenes[$j], 0 , 4) ne substr($thisgenes[$j], 0, 4))
       {$lastgenes[$j] = $thisgenes[$j];$lastpos[$j] = $i;}
       elsif(abs($gene2pos{$lastgenes[$j]}-$gene2pos{$thisgenes[$j]}) > 50)
       {$lastgenes[$j] = $thisgenes[$j];$lastpos[$j] = $i;}
       else
       {
         for(my $p=$lastpos[$j]+1; $p<$i; $p++)
         {$table[$p][$j] = ".";}
         $lastpos[$j] = $i;
         $lastgenes[$j] = $thisgenes[$j];
       } 
    }
  }
}
################################################

for(my $i=0; $i<$tcgenenum; $i++)
{
  my $depth = 0;
  for(my $j=0; $j<=2; $j++)
  {
# print "######################6"." ".$table[$i][$j]."\n";

     if($table[$i][$j] =~ /$Sp_species_name/ || $table[$i][$j] eq ".")
     {
       $depth ++;
     }
     print TB $table[$i][$j].",";
  }
  print TB "$depth\n";
}

sub min(){if($_[0]<$_[1]){return $_[0];}else{return $_[1];}}
sub max(){if($_[0]>$_[1]){return $_[0];}else{return $_[1];}}

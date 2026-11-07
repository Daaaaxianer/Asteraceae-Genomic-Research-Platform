#!/usr/bin/perl
# Step 2: convert the comma-separated mc table to a tab-separated table
# (the trailing "depth" column is dropped).
#
# Usage: perl step2_to_tab.pl IN.mc.txt OUT.mc.tab.txt
use strict;

die "Usage: perl $0 IN.mc.txt OUT.mc.tab.txt\n" if @ARGV < 2;
my ($infile, $outfile) = @ARGV;
open(IN, $infile) or die "cannot open $infile due to $!.\n";
open(OUT, ">", $outfile) or die "cannot open $outfile due to $!.\n";

while (<IN>) {
    s/[\n\r]//g;
    my @array = split(/,/, $_);
    print OUT join("\t", @array[0 .. 4]), "\n";
}
close IN;
close OUT;

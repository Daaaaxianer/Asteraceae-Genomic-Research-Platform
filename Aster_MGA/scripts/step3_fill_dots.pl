#!/usr/bin/perl
# Step 3: fill every empty cell of the tab-separated mc table with ".".
# Columns: Elu gene, A1, A2, A3, A4.
#
# Usage: perl step3_fill_dots.pl IN.mc.tab.txt OUT.mc.tab.dot.txt
use strict;

die "Usage: perl $0 IN.mc.tab.txt OUT.mc.tab.dot.txt\n" if @ARGV < 2;
my ($infile, $outfile) = @ARGV;
open(IN, $infile) or die "cannot open $infile due to $!.\n";
open(OUT, ">", $outfile) or die "cannot open $outfile due to $!.\n";

while (<IN>) {
    s/[\n\r]//g;
    my @a = split(/\t/, $_, -1);
    # fill all five columns (the original script stopped at the fourth,
    # which left the A4 column with blanks)
    for (my $i = 0; $i <= 4; $i++) {
        $a[$i] = "." if !defined $a[$i] || $a[$i] !~ /\w/;
    }
    print OUT join("\t", @a), "\n";
}
close IN;
close OUT;

#!/usr/bin/perl

if ($#ARGV < 0) {
    print <<"DOCUMENTATION";
USAGE: $0 INI-FILE
OUTPUT: STDOUT
SIDE-EFFECTS: NONE

Format an INI type file for insertion into ACF.  Removes comments, and
trailing whitespace.  

In the input file, lines of the same tag type are grouped under [TAG].
When the tag is specified as [TAG#], the acf lines are numbered and
the number of lines of a tag type are reported when a new tag is
encountered or the end of file is reached.

Appropriate for numbered tags: LINE, PARAMETER, CONSTANT, TAPLINE

This code is NOT smart enough to know if you use the same tag in
two disjoint parts of the INI file.

DOCUMENTATION
    exit;
}

#defaults
$enumerate = 0;
#inputs
($infile) = @ARGV;

open(FILE,"<$infile");
$jj=0;
LINE: while (<FILE>) {
    # look for TAGs
    if (m/^\[(.*?)(#?)\]/) {
        if ($enumerate){
            push @newstuff, $TAG."S=$jj\n";
        }
        $TAG = $1;
        if ($2) {
            $enumerate = 1;
            $jj = 0;
            push @TAGS, $TAG;
            next LINE;
        } 
        else {
            $enumerate = 0;
            foreach $tag_encountered (@TAGS) {
                if ($TAG eq $tag_encountered){
#                    print $TAG."  ".$tag_encountered."\n";
                    next LINE;
                }
            }
            push @TAGS, $TAG;
        }
    }
    s/#.*//;        # remove comments
    s/\s*$//;       # remove trailing whitespace
    if ($enumerate) {
        # enclose lines with whitespace, ',' ';' or '=' in double quotes
        if (m/[\s,;=]/) {
            push @newstuff, "$TAG$jj=\"$_\"\n";
            $jj++;
        # otherwise take non-empty lines at face value.
        } elsif (m/./) {
            push @newstuff, "$TAG$jj=$_\n";
            $jj++;
        }
    }
    elsif (m/./) {
        push @newstuff, $_."\n";
    }
}
# push index for last tag onto output array.
push @newstuff, $TAG."S=$jj\n" if ($enumerate);
close(FILE);

# print output array to STDOUT.
print @newstuff;

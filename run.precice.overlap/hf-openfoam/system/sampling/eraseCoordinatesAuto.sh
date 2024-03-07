#!/bin/sh
snapsDIR=$1
coordFILE=$2
endFlag=$3
lastTimeErase=$4
cronEraseFlag=$5

#- File paths
# outDIR=$parentDIR/postProcessing/internalField # /<time>/cloud_*.xy
# coordFILE=$parentDIR/system/sampling/pointCloud.dat
outDIR=$snapsDIR # /<time>/cloud_*.xy
coordFILE=$coordFILE
echo "Post-processing directory:" $outDIR

# #- Variables for OPTION 1
# UFile=cloud_U.xy
# pFile=cloud_p.xy

#- Variables for OPTION 2.1
#- Declare variable types
#- See: https://stackoverflow.com/a/8880633/7473705
declare -a scaList=("p" "p_rgh" "T" "Tprime" "k" "kSGS" "kSGSmean" "kappat" "nuSgs" "nuSGSmean" "nut" "omega")
declare -a vecList=("U" "Uprime")
declare -a tenList=("Rmean")

tmpFile=cloudData.tmp

#- Tracking files
if [ $cronEraseFlag -eq 1 ]; then
    snapsOld=$outDIR/list0.tmp
    snapsNew=$outDIR/list1.tmp
    snapsDif=$outDIR/listDif.tmp

    #- Initialize files
    mkdir -p $outDIR
    touch $snapsOld
    touch $snapsNew
    touch $snapsDif

    #- Populate file lists
    #- See: https://superuser.com/a/716012/1140702
    /usr/bin/ls -A -1v $outDIR | grep -E '^[0-9.]+$' > $snapsNew 2>&1

    #- Delete last line of updated list in case it is active
    if [ $endFlag -eq 0 ] ; then
        head -n -1 $snapsNew &>/dev/null
    fi

    #- Find updated snapshots
    #- See: https://stackoverflow.com/a/35643942/7473705
    comm -13 --nocheck-order $snapsOld $snapsNew > $snapsDif 2>&1

    #- Sort file list
    sort -g $snapsDif > $tmpFile 2>&1
    mv $tmpFile $snapsDif

elif [ $cronEraseFlag -eq 0 ]; then
    snapsDif=$outDIR/listDif.tmp

    #- Initialize files
    mkdir -p $outDIR
    touch $snapsDif

    #- Populate file lists
    #- See: https://superuser.com/a/716012/1140702
    /usr/bin/ls -A -1v $outDIR | grep -E '^[0-9.]+$' > $snapsDif 2>&1

    #- Sort file list
    sort -g $snapsDif > $tmpFile 2>&1
    mv $tmpFile $snapsDif

    #- Remove time steps
    if [ "$lastTimeErase" != "none" ]; then
        #- Find line number corresponding to $lastTimeErase
        lineNumberLastTime=$(grep -nF "$lastTimeErase" $snapsDif | cut -d : -f 1)
        #- Remove lines 
        sed -i '1,'${lineNumberLastTime}'d' $snapsDif
    fi
fi

#- Loop through directories and erase coordinates
updateCoordFlag=1
if [ -s $snapsDif ]; then
    echo "Erasing coordinates ..."
    cat $snapsDif | while read time || [[ -n $time ]]; do
        echo $time

        # #- OPTION 1 (Individual checks)
        # UPath=$outDIR/$time/$UFile
        # if [ -f $UPath ]; then
        #     nUCol=$(awk '{print NF}' $UPath | sort -nu | tail -n 1)
        #     if [ "$nUCol" -gt 3 ]; then  
        #         awk '{printf("%s\t%s\t%s\n", $4, $5, $6)}' $UPath > $tmpFile 2>&1
        #         mv $tmpFile $UPath
        #     fi
        # fi
        # TPath=$outDIR/$time/$TFile
        # if [ -f $TPath ]; then
        #     nTCol=$(awk '{print NF}' $TPath | sort -nu | tail -n 1)
        #     if [ "$nTCol" -gt 3 ]; then  
        #         awk '{printf("%s\n", $4)}' $TPath > $tmpFile 2>&1
        #         mv $tmpFile $TPath
        #     fi
        # fi

        # #- OPTION 2 (Global check, more robust)
        # Loop over files
        #- See: https://stackoverflow.com/a/13446273/7473705
        for xyPath in $outDIR/$time/*.xy; do
            echo $xyPath

            #- OPTION 2.1
            #- Gather fields from filenames
            #- See: https://stackoverflow.com/a/2664758/7473705
            xyFile=$(basename "$xyPath" .xy)
            xyFields=${xyFile#cloud_}
            arrFields=(${xyFields//_/ })
            # 
            #- Correction for fields containing '_'
            #- Example: p_rgh
            if [[ " ${arrFields[*]} " =~ " rgh " ]]; then
                #- Count occureences of 'p' 
                #- See: https://www.computerhope.com/unix/bash/let.htm
                let countp=0
                for x in ${arrFields[*]}; do
                    if [ $x == 'p' ]; then
                        countp=$((countp+1))
                    fi
                done
                #
                #- Remove 'p', 'rgh'
                #- Note: In case of multiple entries 'p', all instances are removed.
                #- See: https://stackoverflow.com/a/16861932/7473705
                delete=(p rgh)
                for target in "${delete[@]}"; do
                    for i in "${!arrFields[@]}"; do
                        if [[ ${arrFields[i]} = $target ]]; then
                            unset 'arrFields[i]'
                        fi
                    done
                done
                #- Fill gaps
                for i in "${!arrFields[@]}"; do
                    arrFieldsTmp+=( "${arrFields[i]}" )
                done
                arrFields=("${arrFieldsTmp[@]}")
                unset arrFieldsTmp
                #
                # Add new element at the end of the array
                if [[ "$countp" -eq 1 ]]; then
                    arrFields+=("p_rgh")
                elif [[ "$countp" -eq 2 ]]; then
                    arrFields+=("p" "p_rgh")
                fi
            fi
            #
            #- Check: e.g. echo ${arrFields[0]} 
            # 
            #- Count target columns that will be left after removing coordinates
            #- See: https://stackoverflow.com/a/15394738/7473705
            nColTgt=0
            for fld in "${arrFields[@]}"; do
                if [[ " ${scaList[*]} " =~ " ${fld} " ]]; then
                    nColTgt=$((nColTgt+1))
                elif [[ " ${vecList[*]} " =~ " ${fld} " ]]; then
                    nColTgt=$((nColTgt+3))
                elif [[ " ${tenList[*]} " =~ " ${fld} " ]]; then
                    nColTgt=$((nColTgt+6))
                fi
            done
            # 
            #- Count actual columns in file
            nCol=$(awk '{print NF}' $xyPath | sort -nu | tail -n 1)
            # 
            #- Save sampled coordinates
            if [ $updateCoordFlag -eq 1 ]; then
                numLinesOld=$(sed -n '$=' $coordFILE)
                numLinesNew=$(sed -n '$=' $xyPath)
                #- SEE: https://serverfault.com/a/7509 (-z)
                if [ -z "${numLinesOld}" ] || [ "$numLinesOld" -gt "$numLinesNew" ]; then
                    dname=$(dirname "$coordFILE")
                    fname=$(basename -- "$coordFILE")
                    fname="${fname%.*}"
                    cut -f 1-3 $xyPath > ${dname}/${fname}.xy
                    updateCoordFlag=0
                    echo "Coordinates file updated using reference from: $(basename $(dirname $xyPath))/$(basename $xyPath) -- Original size: $numLinesOld, New size: $numLinesNew"
                fi
            fi
            # 
            #- Delete columns 
            if [ "$nCol" -gt "$nColTgt" ]; then  
                # awk '{$1=""; $2=""; $3=""; sub("\t", "\t", "\t"); print}' $xyPath > $tmpFile
                cut -f4- $xyPath > $tmpFile

                # #- Add new at the end of file
                # sed -i -e '$a\' $tmpFile
                
                mv $tmpFile $xyPath
            fi

            # #- OPTION 2.2
            # #- Delete first 3 columns
            # #- See: https://unix.stackexchange.com/a/222123/448324
            # cut -f4- $xyPath > $tmpFile
            # mv $tmpFile $xyPath

            #- Count columns in output file
            nColOut=$(awk '{print NF}' $xyPath | sort -nu | tail -n 1)

            echo "File: $(basename $(dirname $xyPath))/$(basename $xyPath) -- Original columns: $nCol, Target columns: $nColTgt, Output columns: $nColOut"

        done
    done
fi

#- Initialize tracking files for next iteration
if [ $endFlag -eq 0 -a $cronEraseFlag -eq 1 ] ; then
    cp $snapsNew $snapsOld
    > $snapsNew
fi
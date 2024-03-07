#!/bin/bash
#----------------------------------------------------------------------------
# Bash script to create formatted snapshots files from simulation output
# Created By  : Nishant Kumar
# Created Date: 21/05/2022
# ---------------------------------------------------------------------------
#- Parse arguments
#- SEE: https://askubuntu.com/a/995110/446303
inputFILE="./preProcessing/userInput.json"
timeList=$1
timeListSamples=$2
parentDIR=$3
snapsOutDIR=$4
shift 4
arrFields=("$@")

#- Logging
echo -e "\n"
echo "###### createSnapshots ######"
echo "arrFields:" "${arrFields[*]}"
echo "timeList:" $timeList
echo "parentDIR:" $parentDIR
echo "snapsOutDIR:" $snapsOutDIR

#- Relative paths to directories in preProcessing/input/samplePaths.dat
snapsRELPATH=postProcessing/internalField
coordRELPATH=system/sampling/pointCloud.dat
# snapsRELPATH=postProcessing/boundaryField
# coordRELPATH=system/sampling/getBoundaryPoints/faceCenter.xy

#- Flags
#- Perform masking, uses python script
maskFLAG=0
#- First pass of xy data file
firstDataPassFLAG=1

#- Create array of paths for each sample point
arrSampleRuns=($(jq -r ".sampleDirectories[]" $inputFILE | tr "\n" " "))

#- Read and format snapshots
#- OPTION 1: Create symbolic link
sampleCnt=0
for sampleRunDIR in "${arrSampleRuns[@]}"; do
    let sampleCnt++
    snapsInDIR=$sampleRunDIR/${snapsRELPATH}
    coordFILE=$sampleRunDIR/${coordRELPATH}
    #- Symbolic link
    cat $timeList | while read tStep || [[ -n $tStep ]]; do
        # echo $tStep
        snapsOutTimeDIR=${snapsOutDIR}/${sampleCnt}.$tStep
        ln -sf $snapsInDIR/$tStep $snapsOutTimeDIR
    done
    #- Get coordinate file
    dname=$(dirname "$coordFILE")
    fname=$(basename -- "$coordFILE")
    fname="${fname%.*}"
    coordxyFILE=${dname}/${fname}.xy
    if [ -f $coordxyFILE ]; then
        coordInFILE=$coordxyFILE
    else
        coordInFILE=$coordFILE
    fi
    #- Get coordinate file name and extension
    coordInFILENAME=$(basename -- "${coordInFILE}") #- >> name.ext
    coordInFILEEXT="${coordInFILENAME##*.}" #- >> ext
    coordInFILENAME="${coordInFILENAME%.*}" #- >> name
    #- Copy coordinate files to `snapsOutDIR`
    coordOutFILE=$snapsOutDIR/${coordInFILENAME}.${coordInFILEEXT}
    cp $coordInFILE $coordOutFILE
done

# #- OPTION 2: Copy snapshots to output time directory <run#.time> in `snapsOutDIR`
# # conda init bash
# # conda activate /gpfs/home/nkumar001/anaconda3/envs/sowfa
# pythonPATH="/gpfs/home/nkumar001/anaconda3/envs/sowfa/bin/python"
# #- Variables
# declare -a scaList=("p" "p_rgh" "T" "Tprime" "k" "kSGS" "kSGSmean" "kappat" \
#     "nuSgs" "nuSGSmean" "nut" "nuTilda" "omega")
# declare -a vecList=("U" "Uprime")
# declare -a tenList=("Rmean")
# sampleCnt=0
# for sampleRunDIR in "${arrSampleRuns[@]}"; do
#     let sampleCnt++
#     snapsInDIR=$sampleRunDIR/${snapsRELPATH}
#     coordFILE=$sampleRunDIR/${coordRELPATH}
#     cat $timeList | while read tStep || [[ -n $tStep ]]; do
#         # echo $tStep
#         snapsOutTimeDIR=${snapsOutDIR}/${sampleCnt}.$tStep
#         mkdir -p $snapsOutTimeDIR
#         #- Loop over files
#         for xyPath in $snapsInDIR/$tStep/*.xy; do
#             # echo $xyPath
#             #- Gather fields from filenames
#             #- SEE: https://stackoverflow.com/a/2664758/7473705
#             xyFile=$(basename "$xyPath" .xy)
#             xyFields=${xyFile#cloud_}
#             arrAvailFields=(${xyFields//_/ })
#             # 
#             #- Correction for fields containing '_'
#             #- Example: p_rgh
#             if [[ " ${arrAvailFields[*]} " =~ " rgh " ]]; then
#                 #- Count occurence of 'p' 
#                 #- SEE: https://www.computerhope.com/unix/bash/let.htm
#                 let countp=0
#                 for x in ${arrAvailFields[*]}; do
#                     if [ $x == 'p' ]; then
#                         countp=$((countp+1))
#                     fi
#                 done
#                 #
#                 #- Remove 'p', 'rgh'
#                 #- Note: In case of multiple 'p', all instances are removed.
#                 #- SEE: https://stackoverflow.com/a/16861932/7473705
#                 rmFields=(p rgh)
#                 for target in "${rmFields[@]}"; do
#                     for i in "${!arrAvailFields[@]}"; do
#                         if [[ ${arrAvailFields[i]} = $target ]]; then
#                             unset 'arrAvailFields[i]'
#                         fi
#                     done
#                 done
#                 #- Fill gaps
#                 for i in "${!arrAvailFields[@]}"; do
#                     arrTmp+=( "${arrAvailFields[i]}" )
#                 done
#                 arrAvailFields=("${arrTmp[@]}")
#                 unset arrTmp
#                 #
#                 # Add new element at the end of the array
#                 if [[ "$countp" -eq 1 ]]; then
#                     arrAvailFields+=("p_rgh")
#                 elif [[ "$countp" -eq 2 ]]; then
#                     arrAvailFields+=("p" "p_rgh")
#                 fi
#             fi
#             # 
#             #- Count target columns that will be left after removing coordinates
#             #- See: https://stackoverflow.com/a/15394738/7473705
#             nColTgt=0
#             for fld in "${arrAvailFields[@]}"; do
#                 if [[ " ${scaList[*]} " =~ " ${fld} " ]]; then
#                     nColTgt=$((nColTgt+1))
#                 elif [[ " ${vecList[*]} " =~ " ${fld} " ]]; then
#                     nColTgt=$((nColTgt+3))
#                 elif [[ " ${tenList[*]} " =~ " ${fld} " ]]; then
#                     nColTgt=$((nColTgt+6))
#                 fi
#             done
#             # 
#             #- Count actual columns in file
#             nCol=$(awk '{print NF}' $xyPath | sort -nu | tail -n 1)
#             #- Delete columns 
#             if [ $nCol -gt $nColTgt ]; then  
#                 echo "DATA COLUMNS MISMATCH ERROR: \
#                     Needed $nColTgt, found $nCol in $xyPath."
#                 exit 1
#             fi
#             #- Get coordinates
#             if [ $firstDataPassFLAG -eq 1 ]; then
#                 #- Save sampled coordinates
#                 nLinesOld=$(sed -n '$=' $coordFILE)
#                 nLinesNew=$(sed -n '$=' $xyPath)
#                 #- Update variable `coordFILE`
#                 dname=$(dirname "$coordFILE")
#                 fname=$(basename -- "$coordFILE")
#                 fname="${fname%.*}"
#                 if [ $nLinesOld -ne $nLinesNew ]; then
#                     coordxyFILE=${dname}/${fname}.xy
#                     if [ -f $coordxyFILE ]; then
#                         coordInFILE=$coordxyFILE
#                     else
#                         echo "GRID POINTS MISMATCH ERROR: ${coordxyFILE} not found."
#                         exit 1
#                     fi
#                 else
#                     coordInFILE=$coordFILE
#                 fi
#                 #- Get coordinate file name and extension
#                 #- SEE: https://stackoverflow.com/a/965072/7473705
#                 coordInFILENAME=$(basename -- "${coordInFILE}") #- >> name.ext
#                 coordInFILEEXT="${coordInFILENAME##*.}" #- >> ext
#                 coordInFILENAME="${coordInFILENAME%.*}" #- >> name
#                 #- Copy coordinate files to `snapsOutDIR`
#                 coordOutFILE=$snapsOutDIR/${coordInFILENAME}.${coordInFILEEXT}
#                 cp $coordInFILE $coordOutFILE
#                 if [ $maskFLAG -eq 1 ]; then
#                     #- Output file names
#                     coordMaskFILE=$snapsOutDIR/${coordInFILENAME}.mask
#                     coordMaskIndFILE=$coordMaskFILE.index
#                     # echo "coordOutFILE:" "$coordOutFILE"
#                     # echo "coordMaskFILE:" "$coordMaskFILE"
#                     #- Get mask index
#                     $pythonPATH ${parentDIR}/preProcessing/createMask.py \
#                         $coordOutFILE $coordMaskFILE $coordMaskIndFILE
#                     #- Read mask index
#                     # readarray -t maskInd < $coordMaskIndFILE
#                 fi
#             fi
#             #- Copy field if size(arrAvailFields)==1
#             #- SEE: https://stackoverflow.com/a/13101899/7473705
#             if [ "${#arrAvailFields[@]}" -eq 1 ]; then
#                 snapOutFILE=${snapsOutTimeDIR}/$(basename -- "$xyPath")
#                 cp $xyPath $snapOutFILE
#             #- Split fields
#             else
#                 fldCnt=0
#                 for availFld in "${arrAvailFields[@]}"; do
#                     let fldCnt++
#                     if [[ " ${arrFields[*]} " =~ " ${availFld} " ]]; then
#                         #- Find the index of the field variable
#                         if [[ " ${scaList[*]} " =~ " ${availFld} " ]]; then
#                             getInd=( $fldCnt )
#                         elif [[ " ${vecList[*]} " =~ " ${availFld} " ]]; then
#                             getInd=($(seq $((3*fldCnt-2)) 1 $((3*fldCnt))))
#                         elif [[ " ${tenList[*]} " =~ " ${availFld} " ]]; then
#                             getInd=($(seq $((6*fldCnt-5)) 1 $((6*fldCnt))))
#                         fi
#                         #- Extract field 
#                         #- SEE: https://stackoverflow.com/a/6312595/7473705
#                         ib="${getInd[0]}" #- begin index
#                         ie="${getInd[@]: -1}" #- end index
#                         snapOutFILE=${snapsOutTimeDIR}/cloud_${availFld}.xy
#                         cut -f $ib-$ie $xyPath > $snapOutFILE
#                     fi
#                 done                
#             fi
#             #- Mask lines
#             if [ $maskFLAG -eq 1 ]; then
#                 #- OPTION 1: Fails with 'too many arguments'
#                 # sed -i ''"${maskInd[*]/%/d;}"'' $snapOutFILE
#                 #- OPTION 2: Painfully slow
#                 # for lineN in "${maskInd[@]}"; do
#                 #     sed -i "${lineN}d" $snapOutFILE
#                 # done
#                 #- OPTION 3
#                 #- SEE: https://stackoverflow.com/a/26727351/7473705
#                 awk 'NR==FNR {del[$1]; next} !(FNR in del)' \
#                     $coordMaskIndFILE $snapOutFILE > ${snapOutFILE}.tmp \
#                     && mv ${snapOutFILE}.tmp $snapOutFILE
#             fi
#             firstDataPassFLAG=0
#         done
#     done
# done

#- Generate list of times <run#.time>
/usr/bin/ls -A -1v $snapsOutDIR | grep -E '^[0-9.]+$' | LC_ALL=C sort -g > $timeListSamples 2>&1
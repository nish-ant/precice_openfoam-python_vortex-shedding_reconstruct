#!/bin/bash
#----------------------------------------------------------------------------
# Bash script to create time list in given range of snapshots and time step
# Created By  : Nishant Kumar
# Created Date: 21/05/2022
# ---------------------------------------------------------------------------
#- Parse input arguments
timeList=$1
timeListSamples=$2
runType=${3:-"init"}

#- Input file
if [ "$runType" == "init" ]; then
    inputFILE="./preProcessing/userInput.json"
elif [ "$runType" == "predict" ] || [ "$runType" == "predictOT" ]; then
    inputFILE="./postProcessing/userInput.predict.json"
fi

tStart=$(jq '.snapTimes.tStart' $inputFILE)
tEnd=$(jq '.snapTimes.tEnd' $inputFILE)
#- NOTE: nSkip=0,1 --> No skipping
nSkip=$(jq '.snapTimes.nSkip' $inputFILE)

sampleDIRS=($(jq -r ".sampleDirectories[]" $inputFILE | tr "\n" " "))
snapsDIR0=${sampleDIRS[0]}/postProcessing/internalField
# snapsDIR0=${sampleDIRS[0]}/postProcessing/boundaryField

#- Logging
echo -e "\n"
echo "####### createTimeList ######"
echo "tStart:" $tStart
echo "tEnd:" $tEnd
echo "nSkip:" $nSkip
echo "timeList:" $timeList

#- Set locale 
#- SEE: https://stackoverflow.com/a/28238855/7473705
LC_NUMERIC=en_US.UTF-8

#- Generate list of times
/usr/bin/ls -A -1v $snapsDIR0 | grep -E '^[0-9.]+$' | LC_ALL=C sort -g \
    > $timeList 2>&1

#- Find lines corresponding to time range
#- See: https://stackoverflow.com/a/47541176/7473705
lineNumStart="$(grep -n -m 1 $tStart $timeList | cut -d: -f1)"
lineNumEnd="$(grep -n -m 1 $tEnd $timeList | cut -d: -f1)"

#- Trim to time range
#- SEE: https://stackoverflow.com/a/2237656/7473705
sed -i -n "${lineNumStart},${lineNumEnd}p" $timeList

#- Skip lines
#- SEE: https://superuser.com/a/396557/1140702
if [ "$nSkip" -gt 0 ]; then
    sed -i -n "1~${nSkip}p" $timeList
fi

#- Generate list of times <run#.time>
#- NOTE: Optional - only when not a new POD run; otherwise already implemented in createSnapshots.sh 
#- SEE: https://stackoverflow.com/a/9463148/7473705
sampleCnt=${#sampleDIRS[@]}
rm -rf $timeListSamples
cnt=1
while [[ $cnt -le $sampleCnt ]]; do
    #- SEE: https://stackoverflow.com/a/19831852/7473705
    prefix=${cnt}'.'
    awk -v prefix="$prefix" '$0=prefix$0' $timeList >> $timeListSamples
    let cnt++
done
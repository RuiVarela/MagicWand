#!/bin/bash
echo "Sample Script"

echo "Arguments Begin:"
counter=0
for var in "$@"
do
    echo "$counter : $var"
    counter=$((counter+1))
done
echo "Arguments End."

#sleep .5
echo "Program Done."
#exit 5

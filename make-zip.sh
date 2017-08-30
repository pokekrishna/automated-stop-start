#!/bin/bash

echo "commenting lambda_handler calls"
sed -i -e 's/^lambda_handler/#lambda_handler/' main.py

echo "moving old zip to /tmp"
mv automated-stop-start.zip /tmp/


echo "zipping following files:"
ls main.py automation/*py

echo "creating a fresh zip"
zip -r automated-stop-start.zip main.py automation/*py


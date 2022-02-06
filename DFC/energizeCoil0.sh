#! /bin/sh

../numato.py "gpio iomask ff"    # address all pins
../numato.py "gpio iodir 00"     # output mode

../numato.py "gpio writeall 00"  # set to zero
sleep 1

for n in `seq 0 1`; do
    n=$(($n + 64))              # turn on the "enable" signal
    ch=`printf %02x $n`
    echo $ch
    ../numato.py "gpio writeall $ch"
    sleep 5
    ../numato.py "gpio writeall 00"
    sleep 1
done



def checksumValidator(packet:bytes) -> bool:
    checksum = 0
    for byte in packet[1:-5]:
        checksum ^= byte

    highNibbleAscii, lowNibbleAscii = ord(hex((checksum >> 4) & 0xf)[-1]).to_bytes(1, 'big'), ord(hex((checksum) & 0xf)[-1]).to_bytes(1, 'big')
    highInput, lowInput = packet[-4], packet[-3]

    if highNibbleAscii == highInput.to_bytes(1,'big') and lowNibbleAscii == lowInput.to_bytes(1,'big'):
        return True
    else:
        return False

def packetRepairer(packet:bytes, repairLimit:int=1) -> tuple[bytes, bool, bool] :
    """
    """
    valid = False
    repaired = False
    errors = []

    # Check for how many error bits are in packet
    for index, byte in enumerate(packet[1:-4]):
        if byte == 127:
            errors.append(index)

    if len(errors) == 0: # If no error bits are detected do a checksum validation
        if checksumValidator: # If checksum is good return original packet and stats
            outPacket = packet
            valid = True
            repaired = False
        else: # if checksum is bad return original packet and fail
            outPacket = packet
            valid = False
            repaired = False

    if len(errors) <= repairLimit: # If number of errors is lower than set repair limit attempt to repair the packet
        testSolution = [44]*len(errors)
        bottomAscii = 44 # ","
        topAscii = 90 # "Z"
        asciiRange = topAscii-bottomAscii

        for i in range(pow(asciiRange,len(errors))): # Repair is O^n complexity due to needing to search for a solution through all available values.

            #Test replacing error bits with test bits then check validation
            testPacket = packet
            for errorIndex, errorFix in zip(errors,testSolution):
                testPacket = testPacket.replace(b'\x7F', errorFix.to_bytes(1,'big'), 1)
            
            if checksumValidator(testPacket):
                outPacket = testPacket
                valid = True
                repaired = True
                return outPacket, valid, repaired
            
            #Increment through ascii bits combinations
            for index, testChar in enumerate(testSolution):
                if index == 0:
                    if testChar == topAscii:
                        testSolution[index] = bottomAscii
                    else:
                        testSolution[index] +=1
                else:
                    if testSolution[index-1] == topAscii:
                        if testChar == topAscii:
                            testSolution[index] = bottomAscii
                        else:
                            testSolution[index] +=1
        # If no solutions are found return original packet and fail
        valid = False
        repaired = False
        outPacket = packet
              
    else: # If number of errors are above repair limit give up life is hopeless
        valid = False
        repaired = False
        outPacket = packet


    return outPacket, valid, repaired
        
if __name__ == "__main__":
    gps_test = "$GNGSA,A,3,2,20,06,,,,,,,,,,6.12,4.134.51,1*06\r\n"
    
    gps_tp = "$GPGSV,3,3,10,25,11,232,17,29,02,286,,1*62\r\n"

    #print(checksumValidator(bytes(gps_tp,"utf-8")))
    

    output = packetRepairer(bytes(gps_test,"utf-8"), repairLimit=2)
    print(output)
    

        
        
       
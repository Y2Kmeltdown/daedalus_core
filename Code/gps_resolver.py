import os


gps_test = "$GPGSV,3,3,10,25,11,232,17,29,02,286,,1*62\r\n"


def packetRepairer(packet:bytes, repairLimit:int=1) -> tuple[bytes, bool, bool] :
    """
    """
    def checksumValidator(packet:bytes) -> bool:
        checksum = 0
        for byte in packet[1:-4]:
            checksum ^= byte

        highNibbleAscii, lowNibbleAscii = ord(hex((checksum >> 4) & 0xf)[-1]).to_bytes(1, 'big'), ord(hex((checksum) & 0xf)[-1]).to_bytes(1, 'big')
        highInput, lowInput = packet[-3], packet[-2]
        
        if highNibbleAscii == highInput and lowNibbleAscii == lowInput:
            return True
        else:
            return False
        
    
    valid = False
    repaired = False
    errors = []
    for index, byte in enumerate(packet[1:-4]):
        if byte == 127:
            errors.append(index)
    if len(errors) == 0:
        if checksumValidator:
            outPacket = packet
            valid = True
            repaired = False
        else:
            outPacket = packet
            valid = False
            repaired = False
    if len(errors) <= repairLimit:
        #Underneath Repair Limit Attempt repairing
        # figure out how to adjust depth of 
        pass
    else:
        valid = False
        repaired = False
        outPacket = packet
    
    return outPacket, valid, repaired
        

    

        
        
       
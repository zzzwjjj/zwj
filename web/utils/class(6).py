def discover_devices(duration=8, flush_cache=True, lookup_names=False,
                     lookup_class=False, device_id=-1, iac=IAC_GIAC):
    if device_id == -1:
        device_id = _bt.hci_get_route()

    sock = _gethcisock(device_id)
    try:
        results = _bt.hci_inquiry(sock, duration=duration, flush_cache=True,
                                  lookup_class=lookup_class, device_id=device_id,
                                  iac=iac)
    except _bt.error as e:
        sock.close()
        raise BluetoothError(e.args[0], "Error communicating with local "
                                        "bluetooth adapter: " + e.args[1])

    if lookup_names:
        pairs = []
        for item in results:
            if lookup_class:
                addr, dev_class = item
            else:
                addr = item
            timeoutms = int(10 * 1000)
            try:
                name = _bt.hci_read_remote_name(sock, addr, timeoutms)
            except _bt.error:
                # name lookup failed.  either a timeout, or I/O error
                continue
            pairs.append((addr, name, dev_class) if lookup_class else (addr, name))
        sock.close()
        return pairs
    else:
        sock.close()
        return results


def read_local_bdaddr():
    try:
        hci_sock = _bt.hci_open_dev(0)
        old_filter = hci_sock.getsockopt(_bt.SOL_HCI, _bt.HCI_FILTER, 14)
        flt = _bt.hci_filter_new()
        opcode = _bt.cmd_opcode_pack(_bt.OGF_INFO_PARAM,
                                     _bt.OCF_READ_BD_ADDR)
        _bt.hci_filter_set_ptype(flt, _bt.HCI_EVENT_PKT)
        _bt.hci_filter_set_event(flt, _bt.EVT_CMD_COMPLETE)
        _bt.hci_filter_set_opcode(flt, opcode)
        hci_sock.setsockopt(_bt.SOL_HCI, _bt.HCI_FILTER, flt)

        _bt.hci_send_cmd(hci_sock, _bt.OGF_INFO_PARAM, _bt.OCF_READ_BD_ADDR)

        pkt = hci_sock.recv(255)

        status, raw_bdaddr = struct.unpack("xxxxxxB6s", pkt)
        assert status == 0

        t = ["%02X" % get_byte(b) for b in raw_bdaddr]
        t.reverse()
        bdaddr = ":".join(t)

        # restore old filter
        hci_sock.setsockopt(_bt.SOL_HCI, _bt.HCI_FILTER, old_filter)
        return [bdaddr]
    except _bt.error as e:
        raise BluetoothError(*e.args)


def lookup_name(address, timeout=10):
    if not is_valid_address(address):
        raise BluetoothError(EINVAL, "%s is not a valid Bluetooth address" % address)

    sock = _gethcisock()
    timeoutms = int(timeout * 1000)
    try:
        name = _bt.hci_read_remote_name(sock, address, timeoutms)
    except _bt.error:
        # name lookup failed.  either a timeout, or I/O error
        name = None
    sock.close()
    return name


def set_packet_timeout(address, timeout):
    """
    Adjusts the ACL flush timeout for the ACL connection to the specified
    device.  This means that all L2CAP and RFCOMM data being sent to that
    device will be dropped if not acknowledged in timeout milliseconds (maximum
    1280).  A timeout of 0 means to never drop packets.

    Since this affects all Bluetooth connections to that device, and not just
    those initiated by this process or PyBluez, a call to this method requires
    superuser privileges.

    You must have an active connection to the specified device before invoking
    this method.

    """
    n = round(timeout / 0.625)
    write_flush_timeout(address, n)


def get_l2cap_options(sock):
    """get_l2cap_options (sock, mtu)

    Gets L2CAP options for the specified L2CAP socket.
    Options are: omtu, imtu, flush_to, mode, fcs, max_tx, txwin_size.

    """
    # TODO this should be in the C module, because it depends
    # directly on struct l2cap_options layout.
    s = sock.getsockopt(SOL_L2CAP, L2CAP_OPTIONS, 12)
    options = list(struct.unpack("HHHBBBH", s))
    return options


def set_l2cap_options(sock, options):
    """set_l2cap_options (sock, options)

    Sets L2CAP options for the specified L2CAP socket.
    The option list must be in the same format supplied by
    get_l2cap_options().

    """
    # TODO this should be in the C module, because it depends
    # directly on struct l2cap_options layout.
    s = struct.pack("HHHBBBH", *options)
    sock.setsockopt(SOL_L2CAP, L2CAP_OPTIONS, s)


def set_l2cap_mtu(sock, mtu):
    """set_l2cap_mtu (sock, mtu)

    Adjusts the MTU for the specified L2CAP socket.  This method needs to be
    invoked on both sides of the connection for it to work!  The default mtu
    that all L2CAP connections start with is 672 bytes.

    mtu must be between 48 and 65535, inclusive.

    """
    options = get_l2cap_options(sock)
    options[0] = options[1] = mtu
    set_l2cap_options(sock, options)


def _get_available_ports(protocol):
    if protocol == RFCOMM:
        return range(1, 31)
    elif protocol == L2CAP:
        return range(0x1001, 0x8000, 2)
    else:
        return [0]


class BluetoothSocket:
    __doc__ = _bt.btsocket.__doc__

    def __init__(self, proto=RFCOMM, _sock=None):
        if _sock is None:
            _sock = _bt.btsocket(proto)
        self._sock = _sock
        self._proto = proto

    def dup(self):
        """dup () -> socket object

        Return a new socket object connected to the same system resource.

        """
        return BluetoothSocket(proto=self._proto, _sock=self._sock)

    def accept(self):
        try:
            client, addr = self._sock.accept()
        except _bt.error as e:
            raise BluetoothError(*e.args)
        newsock = BluetoothSocket(self._proto, client)
        return (newsock, addr)

    accept.__doc__ = _bt.btsocket.accept.__doc__

    def bind(self, addrport):
        if len(addrport) != 2 or addrport[1] != 0:
            try:
                return self._sock.bind(addrport)
            except _bt.error as e:
                raise BluetoothError(*e.args)
        addr, _ = addrport
        for port in _get_available_ports(self._proto):
            try:
                return self._sock.bind((addr, port))
            except _bt.error as e:
                err = BluetoothError(*e.args)
                if err.errno != EADDRINUSE:
                    break
        raise err

    def get_l2cap_options(self):
        """get_l2cap_options (sock, mtu)

        Gets L2CAP options for the specified L2CAP socket.
        Options are: omtu, imtu, flush_to, mode, fcs, max_tx, txwin_size.

        """
        return get_l2cap_options(self)

    def set_l2cap_options(self, options):
        """set_l2cap_options (sock, options)

        Sets L2CAP options for the specified L2CAP socket.
        The option list must be in the same format supplied by
        get_l2cap_options().

        """
        return set_l2cap_options(self, options)

    def set_l2cap_mtu(self, mtu):
        """set_l2cap_mtu (sock, mtu)

        Adjusts the MTU for the specified L2CAP socket.  This method needs to be
        invoked on both sides of the connection for it to work!  The default mtu
        that all L2CAP connections start with is 672 bytes.

        mtu must be between 48 and 65535, inclusive.

        """
        return set_l2cap_mtu(self, mtu)

    # import methods from the wraapped socket object
    _s = ("""def %s (self, *args, **kwargs):
    try:
        return self._sock.%s (*args, **kwargs)
    except _bt.error as e:
        raise BluetoothError (*e.args)
    %s.__doc__ = _bt.btsocket.%s.__doc__\n""")
    for _m in ('connect', 'connect_ex', 'close',
               'fileno', 'getpeername', 'getsockname', 'gettimeout',
               'getsockopt', 'listen', 'makefile', 'recv', 'recvfrom', 'sendall',
               'send', 'sendto', 'setblocking', 'setsockopt', 'settimeout',
               'shutdown', 'setl2capsecurity'):
        exec(_s % (_m, _m, _m, _m))
    del _m, _s

    # import readonly attributes from the wrapped socket object
    _s = ("@property\ndef %s (self): \
    return self._sock.%s")
    for _m in ('family', 'type', 'proto', 'timeout'):
        exec(_s % (_m, _m))
    del _m, _s


def advertise_service(sock, name, service_id="", service_classes=[], \
                      profiles=[], provider="", description="", protocols=[]):
    if service_id != "" and not is_valid_uuid(service_id):
        raise ValueError("invalid UUID specified for service_id")
    for uuid in service_classes:
        if not is_valid_uuid(uuid):
            raise ValueError("invalid UUID specified in service_classes")
    for uuid, version in profiles:
        if not is_valid_uuid(uuid) or version < 0 or version > 0xFFFF:
            raise ValueError("Invalid Profile Descriptor")
    for uuid in protocols:
        if not is_valid_uuid(uuid):
            raise ValueError("invalid UUID specified in protocols")

    try:
        _bt.sdp_advertise_service(sock._sock, name, service_id, \
                                  service_classes, profiles, provider, description, \
                                  protocols)
    except _bt.error as e:
        raise BluetoothError(*e.args)


def stop_advertising(sock):
    try:
        _bt.sdp_stop_advertising(sock._sock)
    except _bt.error as e:
        raise BluetoothError(*e.args)


def find_service(name=None, uuid=None, address=None):
    if not address:
        devices = discover_devices()
    else:
        devices = [address]

    results = []

    if uuid is not None and not is_valid_uuid(uuid):
        raise ValueError("invalid UUID")

    try:
        for addr in devices:
            try:
                s = _bt.SDPSession()
                s.connect(addr)
                matches = []
                if uuid is not None:
                    matches = s.search(uuid)
                else:
                    matches = s.browse()
            except _bt.error:
                continue

            if name is not None:
                matches = [s for s in matches if s.get("name", "") == name]

            for m in matches:
                m["host"] = addr

            results.extend(matches)
    except _bt.error as e:
        raise BluetoothError(*e.args)

    return results


# ================ BlueZ internal methods ================
def _gethcisock(device_id=-1):
    try:
        sock = _bt.hci_open_dev(device_id)
    except _bt.error as e:
        raise BluetoothError(e.args[0], "error accessing bluetooth device: " +
                             e.args[1])
    return sock


def get_acl_conn_handle(hci_sock, addr):
    hci_fd = hci_sock.fileno()
    reqstr = struct.pack("6sB17s", _bt.str2ba(addr),
                         _bt.ACL_LINK, b"\0" * 17)
    request = array.array("b", reqstr)
    try:
        fcntl.ioctl(hci_fd, _bt.HCIGETCONNINFO, request, 1)
    except OSError as e:
        raise BluetoothError(e.args[0], "There is no ACL connection to %s" % addr)

    # XXX should this be "<8xH14x"?
    handle = struct.unpack("8xH14x", request.tostring())[0]
    return handle


def write_flush_timeout(addr, timeout):
    hci_sock = _bt.hci_open_dev()
    # get the ACL connection handle to the remote device
    handle = get_acl_conn_handle(hci_sock, addr)
    # XXX should this be "<HH"
    pkt = struct.pack("HH", handle, _bt.htobs(timeout))
    response = _bt.hci_send_req(hci_sock, _bt.OGF_HOST_CTL,
                                0x0028, _bt.EVT_CMD_COMPLETE, 3, pkt)
    status = get_byte(response[0])
    rhandle = struct.unpack("H", response[1:3])[0]
    assert rhandle == handle
    assert status == 0


def read_flush_timeout(addr):
    hci_sock = _bt.hci_open_dev()
    # get the ACL connection handle to the remote device
    handle = get_acl_conn_handle(hci_sock, addr)
    # XXX should this be "<H"?
    pkt = struct.pack("H", handle)
    response = _bt.hci_send_req(hci_sock, _bt.OGF_HOST_CTL,
                                0x0027, _bt.EVT_CMD_COMPLETE, 5, pkt)
    status = get_byte(response[0])
    rhandle = struct.unpack("H", response[1:3])[0]
    assert rhandle == handle
    assert status == 0
    fto = struct.unpack("H", response[3:5])[0]
    return fto


# =============== DeviceDiscoverer ==================
def byte_to_signed_int(byte_):
    if byte_ > 127:
        return byte_ - 256
    else:
        return byte_


class DeviceDiscoverer:
    """
    Skeleton class for finer control of the device discovery process.

    To implement asynchronous device discovery (e.g. if you want to do
    something *as soon as* a device is discovered), subclass
    DeviceDiscoverer and override device_discovered () and
    inquiry_complete ()
    """

    def __init__(self, device_id=-1):
        """
        __init__ (device_id=-1)

        device_id - The ID of the Bluetooth adapter that will be used
                    for discovery.
        """
        self.sock = None
        self.is_inquiring = False
        self.lookup_names = False
        self.device_id = device_id

        self.names_to_find = {}
        self.names_found = {}

    def find_devices(self, lookup_names=True,
                     duration=8,
                     flush_cache=True):
        """
        find_devices (lookup_names=True, service_name=None,
                       duration=8, flush_cache=True)

        Call this method to initiate the device discovery process

        lookup_names - set to True if you want to lookup the user-friendly
                       names for each device found.

        service_name - set to the name of a service you're looking for.
                       only devices with a service of this name will be
                       returned in device_discovered () NOT YET IMPLEMENTED


        ADVANCED PARAMETERS:  (don't change these unless you know what
                            you're doing)

        duration - the number of 1.2 second units to spend searching for
                   bluetooth devices.  If lookup_names is True, then the
                   inquiry process can take a lot longer.

        flush_cache - return devices discovered in previous inquiries
        """
        if self.is_inquiring:
            raise BluetoothError(EBUSY, "Already inquiring!")

        self.lookup_names = lookup_names

        self.sock = _gethcisock(self.device_id)
        flt = _bt.hci_filter_new()
        _bt.hci_filter_all_events(flt)
        _bt.hci_filter_set_ptype(flt, _bt.HCI_EVENT_PKT)

        try:
            self.sock.setsockopt(_bt.SOL_HCI, _bt.HCI_FILTER, flt)
        except _bt.error as e:
            raise BluetoothError(*e.args)

        # send the inquiry command
        max_responses = 255
        cmd_pkt = struct.pack("BBBBB", 0x33, 0x8b, 0x9e, \
                              duration, max_responses)

        self.pre_inquiry()

        try:
            _bt.hci_send_cmd(self.sock, _bt.OGF_LINK_CTL, \
                             _bt.OCF_INQUIRY, cmd_pkt)
        except _bt.error as e:
            raise BluetoothError(*e.args)

        self.is_inquiring = True

        self.names_to_find = {}
        self.names_found = {}

    def cancel_inquiry(self):
        """
        Call this method to cancel an inquiry in process.  inquiry_complete
        will still be called.
        """
        self.names_to_find = {}

        if self.is_inquiring:
            try:
                _bt.hci_send_cmd(self.sock, _bt.OGF_LINK_CTL, \
                                 _bt.OCF_INQUIRY_CANCEL)
            except _bt.error as e:
                self.sock.close()
                self.sock = None
                raise BluetoothError(e.args[0],
                                     "error canceling inquiry: " +
                                     e.args[1])
            self.is_inquiring = False

    def process_inquiry(self):
        """
        Repeatedly calls process_event () until the device inquiry has
        completed.
        """
        while self.is_inquiring or len(self.names_to_find) > 0:
            self.process_event()

    def process_event(self):
        """
        Waits for one event to happen, and proceses it.  The event will be
        either a device discovery, or an inquiry completion.
        """
        self._process_hci_event()

    def _process_hci_event(self):
        # FIXME may not wrap _bluetooth.error properly
        if self.sock is None: return
        # voodoo magic!!!
        pkt = self.sock.recv(258)
        ptype, event, plen = struct.unpack("BBB", pkt[:3])
        pkt = pkt[3:]
        if event == _bt.EVT_INQUIRY_RESULT:
            nrsp = get_byte(pkt[0])
            for i in range(nrsp):
                addr = _bt.ba2str(pkt[1 + 6 * i:1 + 6 * i + 6])
                psrm = pkt[1 + 6 * nrsp + i]
                pspm = pkt[1 + 7 * nrsp + i]
                devclass_raw = struct.unpack("BBB",
                                             pkt[1 + 9 * nrsp + 3 * i:1 + 9 * nrsp + 3 * i + 3])
                devclass = (devclass_raw[2] << 16) | \
                           (devclass_raw[1] << 8) | \
                           devclass_raw[0]
                clockoff = pkt[1 + 12 * nrsp + 2 * i:1 + 12 * nrsp + 2 * i + 2]

                self._device_discovered(addr, devclass,
                                        psrm, pspm, clockoff, None, None)
        elif event == _bt.EVT_INQUIRY_RESULT_WITH_RSSI:
            nrsp = get_byte(pkt[0])
            for i in range(nrsp):
                addr = _bt.ba2str(pkt[1 + 6 * i:1 + 6 * i + 6])
                psrm = pkt[1 + 6 * nrsp + i]
                pspm = pkt[1 + 7 * nrsp + i]
                #                devclass_raw = pkt[1+8*nrsp+3*i:1+8*nrsp+3*i+3]
                #                devclass = struct.unpack ("I", "%s\0" % devclass_raw)[0]
                devclass_raw = struct.unpack("BBB",
                                             pkt[1 + 8 * nrsp + 3 * i:1 + 8 * nrsp + 3 * i + 3])
                devclass = (devclass_raw[2] << 16) | \
                           (devclass_raw[1] << 8) | \
                           devclass_raw[0]
                clockoff = pkt[1 + 11 * nrsp + 2 * i:1 + 11 * nrsp + 2 * i + 2]
                rssi = byte_to_signed_int(get_byte(pkt[1 + 13 * nrsp + i]))

                self._device_discovered(addr, devclass,
                                        psrm, pspm, clockoff, rssi, None)
        elif _bt.HAVE_EVT_EXTENDED_INQUIRY_RESULT and event == _bt.EVT_EXTENDED_INQUIRY_RESULT:
            nrsp = get_byte(pkt[0])
            for i in range(nrsp):
                addr = _bt.ba2str(pkt[1 + 6 * i:1 + 6 * i + 6])
                psrm = pkt[1 + 6 * nrsp + i]
                pspm = pkt[1 + 7 * nrsp + i]
                devclass_raw = struct.unpack("BBB",
                                             pkt[1 + 8 * nrsp + 3 * i:1 + 8 * nrsp + 3 * i + 3])
                devclass = (devclass_raw[2] << 16) | \
                           (devclass_raw[1] << 8) | \
                           devclass_raw[0]
                clockoff = pkt[1 + 11 * nrsp + 2 * i:1 + 11 * nrsp + 2 * i + 2]
                rssi = byte_to_signed_int(get_byte(pkt[1 + 13 * nrsp + i]))

                data_len = _bt.EXTENDED_INQUIRY_INFO_SIZE - _bt.INQUIRY_INFO_WITH_RSSI_SIZE
                data = pkt[1 + 14 * nrsp + i:1 + 14 * nrsp + i + data_len]
                name = None
                pos = 0
                while (pos <= len(data)):
                    struct_len = get_byte(data[pos])
                    if struct_len == 0:
                        break
                    eir_type = get_byte(data[pos + 1])
                    if eir_type == 0x09:  # Complete local name
                        name = data[pos + 2:pos + struct_len + 1]
                    pos += struct_len + 2

                self._device_discovered(addr, devclass,
                                        psrm, pspm, clockoff, rssi, name)
        elif event == _bt.EVT_INQUIRY_COMPLETE or event == _bt.EVT_CMD_COMPLETE:
            self.is_inquiring = False
            if len(self.names_to_find) == 0:
                #                print "inquiry complete (evt_inquiry_complete)"
                self.sock.close()
                self._inquiry_complete()
            else:
                self._send_next_name_req()

        elif event == _bt.EVT_CMD_STATUS:
            # XXX shold this be "<BBH"
            status, ncmd, opcode = struct.unpack("BBH", pkt[:4])
            if status != 0:
                self.is_inquiring = False
                self.sock.close()

                #                print "inquiry complete (bad status 0x%X 0x%X 0x%X)" % \
                #                        (status, ncmd, opcode)
                self.names_to_find = {}
                self._inquiry_complete()
        elif event == _bt.EVT_REMOTE_NAME_REQ_COMPLETE:
            status = get_byte(pkt[0])
            addr = _bt.ba2str(pkt[1:7])
            if status == 0:
                try:
                    name = pkt[7:].split('\0')[0]
                except IndexError:
                    name = ''
                if addr in self.names_to_find:
                    device_class, rssi = self.names_to_find[addr][:2]
                    self.device_discovered(addr, device_class, rssi, name)
                    del self.names_to_find[addr]
                    self.names_found[addr] = (device_class, rssi, name)
                else:
                    pass
            else:
                if addr in self.names_to_find: del self.names_to_find[addr]
                # XXX should we do something when a name lookup fails?
            #                print "name req unsuccessful %s - %s" % (addr, status)

            if len(self.names_to_find) == 0:
                self.is_inquiring = False
                self.sock.close()
                self.inquiry_complete()
            #                print "inquiry complete (name req complete)"
            else:
                self._send_next_name_req()
        else:
            pass

    #            print "unrecognized packet type 0x%02x" % ptype

    def _device_discovered(self, address, device_class,
                           psrm, pspm, clockoff, rssi, name):
        if self.lookup_names:
            if name is not None:
                self.device_discovered(address, device_class, rssi, name)
            elif address not in self.names_found and \
                    address not in self.names_to_find:

                self.names_to_find[address] = \
                    (device_class, rssi, psrm, pspm, clockoff)
        else:
            self.device_discovered(address, device_class, rssi, None)

    def _send_next_name_req(self):
        assert len(self.names_to_find) > 0
        address = list(self.names_to_find.keys())[0]
        device_class, rssi, psrm, pspm, clockoff = self.names_to_find[address]
        bdaddr = _bt.str2ba(address)  # TODO not supported in python3

        cmd_pkt = "{}{}\0{}".format(bdaddr, psrm, clockoff)

        try:
            _bt.hci_send_cmd(self.sock, _bt.OGF_LINK_CTL, \
                             _bt.OCF_REMOTE_NAME_REQ, cmd_pkt)
        except _bt.error as e:
            raise BluetoothError(e.args[0],
                                 "error request name of %s - %s:" %
                                 (address, e.args[1]))

    def fileno(self):
        if not self.sock: return None
        return self.sock.fileno()

    def pre_inquiry(self):
        """
        Called just after find_devices is invoked, but just before the
        inquiry is started.

        This method exists to be overriden
        """

    def device_discovered(self, address, device_class, rssi, name):
        """
        Called when a bluetooth device is discovered.

        address is the bluetooth address of the device

        device_class is the Class of Device, as specified in [1]
                     passed in as a 3-byte string

        name is the user-friendly name of the device if lookup_names was
        set when the inquiry was started.  otherwise None

        This method exists to be overriden.

        [1] https://www.bluetooth.org/foundry/assignnumb/document/baseband
        """
        if name:
            print("found: {} - {} (class 0x{:X}, rssi {})".format(
                address, name, device_class, rssi))
        else:
            print("found: {} (class 0x{:X})".format(address, device_class))
            print("found: {} (class 0x{:X}, rssi {})".format(
                address, device_class, rssi))

    def _inquiry_complete(self):
        """
        Called when an inquiry started by find_devices has completed.
        """
        self.sock.close()
        self.sock = None
        self.inquiry_complete()

    def inquiry_complete(self):
        """
        Called when an inquiry started by find_devices has completed.
        """
        print("inquiry complete")

def is_valid_address (s):
    """returns True if address is a valid Bluetooth address.

    valid address are always strings of the form XX:XX:XX:XX:XX:XX
    where X is a hexadecimal character.  For example,
    01:23:45:67:89:AB is a valid address, but IN:VA:LI:DA:DD:RE is not.

    """
    try:
        pairs = s.split (":")
        if len (pairs) != 6: return False
        if not all(0 <= int(b, 16) <= 255 for b in pairs): return False
    except:
        return False
    return True

def is_valid_uuid (uuid):
    """
    is_valid_uuid (uuid) -> bool

    returns True if uuid is a valid 128-bit UUID.

    valid UUIDs are always strings taking one of the following forms:
    XXXX
    XXXXXXXX
    XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
    where each X is a hexadecimal digit (case insensitive)

    """
    try:
        if len (uuid) == 4:
            if int (uuid, 16) < 0: return False
        elif len (uuid) == 8:
            if int (uuid, 16) < 0: return False
        elif len (uuid) == 36:
            pieces = uuid.split ("-")
            if len (pieces) != 5 or \
                    len (pieces[0]) != 8 or \
                    len (pieces[1]) != 4 or \
                    len (pieces[2]) != 4 or \
                    len (pieces[3]) != 4 or \
                    len (pieces[4]) != 12:
                return False
            [ int (p, 16) for p in pieces ]
        else:
            return False
    except ValueError:
        return False
    except TypeError:
        return False
    return True

def to_full_uuid (uuid):
    """
    converts a short 16-bit or 32-bit reserved UUID to a full 128-bit Bluetooth
    UUID.

    """
    if not is_valid_uuid (uuid): raise ValueError ("invalid UUID")
    if len (uuid) == 4:
        return "0000%s-0000-1000-8000-00805F9B34FB" % uuid
    elif len (uuid) == 8:
        return "%s-0000-1000-8000-00805F9B34FB" % uuid
    else:
        return uuid

# =============== parsing and constructing raw SDP records ============

def sdp_parse_size_desc (data):
    dts = struct.unpack ("B", data[0:1])[0]
    dtype, dsizedesc = dts >> 3, dts & 0x7
    dstart = 1
    if   dtype == 0:     dsize = 0
    elif dsizedesc == 0: dsize = 1
    elif dsizedesc == 1: dsize = 2
    elif dsizedesc == 2: dsize = 4
    elif dsizedesc == 3: dsize = 8
    elif dsizedesc == 4: dsize = 16
    elif dsizedesc == 5:
        dsize = struct.unpack ("B", data[1:2])[0]
        dstart += 1
    elif dsizedesc == 6:
        dsize = struct.unpack ("!H", data[1:3])[0]
        dstart += 2
    elif dsizedesc == 7:
        dsize = struct.unpack ("!I", data[1:5])[0]
        dstart += 4

    if dtype > 8:
        raise ValueError ("Invalid TypeSizeDescriptor byte %s %d, %d" \
                % (binascii.hexlify (data[0:1]), dtype, dsizedesc))

    return dtype, dsize, dstart

def sdp_parse_uuid (data, size):
    if size == 2:
        return binascii.hexlify (data)
    elif size == 4:
        return binascii.hexlify (data)
    elif size == 16:
        return "%08X-%04X-%04X-%04X-%04X%08X" % struct.unpack ("!IHHHHI", data)
    else: return ValueError ("invalid UUID size")

def sdp_parse_int (data, size, signed):
    fmts = { 1 : "!b" , 2 : "!h" , 4 : "!i" , 8 : "!q" , 16 : "!qq" }
    fmt = fmts[size]
    if not signed: fmt = fmt.upper ()
    if fmt in [ "!qq", "!QQ" ]:
        upp, low = struct.unpack ("!QQ", data)
        result = ( upp << 64) | low
        if signed:
            result=- ((~ (result-1))&0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF)
        return result
    else:
        return struct.unpack (fmt, data)[0]


def sdp_make_data_element (type, value):
    def maketsd (tdesc, sdesc):
        return struct.pack ("B", (tdesc << 3) | sdesc)
    def maketsdl (tdesc, size):
        if   size < (1<<8):  return struct.pack ("!BB", tdesc << 3 | 5, size)
        elif size < (1<<16): return struct.pack ("!BH", tdesc << 3 | 6, size)
        else:                return struct.pack ("!BI", tdesc << 3 | 7, size)

    easyinttypes = { "UInt8"   : (1, 0, "!B"),  "UInt16"  : (1, 1, "!H"),
                     "UInt32"  : (1, 2, "!I"),  "UInt64"  : (1, 3, "!Q"),
                     "SInt8"   : (2, 0, "!b"),  "SInt16"  : (2, 1, "!h"),
                     "SInt32"  : (2, 2, "!i"),  "SInt64"  : (2, 3, "!q"),
                     }

    if type == "Nil":
        return maketsd (0, 0)
    elif type in easyinttypes:
        tdesc, sdesc, fmt = easyinttypes[type]
        return maketsd (tdesc, sdesc) + struct.pack (fmt, value)
    elif type == "UInt128":
        ts = maketsd (1, 4)
        upper = ts >> 64
        lower = (ts & 0xFFFFFFFFFFFFFFFF)
        return ts + struct.pack ("!QQ", upper, lower)
    elif type == "SInt128":
        ts = maketsd (2, 4)
        # FIXME
        raise NotImplementedError ("128-bit signed int NYI!")
    elif type == "UUID":
        if len (value) == 4:
            return maketsd (3, 1) + binascii.unhexlify (value)
        elif len (value) == 8:
            return maketsd (3, 2) + binascii.unhexlify (value)
        elif len (value) == 36:
            return maketsd (3, 4) + binascii.unhexlify (value.replace ("-",""))
    elif type == "String":
        return maketsdl (4, len (value)) + str.encode(value)
    elif type == "Bool":
        return maketsd (5,0) + (value and "\x01" or "\x00")
    elif type == "ElemSeq":
        packedseq = bytes()
        for subtype, subval in value:
            nextelem = sdp_make_data_element (subtype, subval)
            packedseq = packedseq + nextelem
        return maketsdl (6, len (packedseq)) + packedseq
    elif type == "AltElemSeq":
        packedseq = bytes()
        for subtype, subval in value:
            packedseq = packedseq + sdp_make_data_element (subtype, subval)
        return maketsdl (7, len (packedseq)) + packedseq
    elif type == "URL":
        return maketsdl (8, len (value)) + value
    else:
        raise ValueError ("invalid type %s" % type)

def discover_devices(duration=8, flush_cache=True, lookup_names=False,
        lookup_class=False, device_id=-1):
    # This is order of discovered device attributes in C-code.
    btAddresIndex = 0
    namesIndex = 1
    classIndex = 2

    # Use lightblue to discover devices on OSX.
    devices = lightblue.finddevices(getnames=lookup_names, length=duration)

    ret = list()
    for device in devices:
        item = [device[btAddresIndex], ]
        if lookup_names:
            item.append(device[namesIndex])
        if lookup_class:
            item.append(device[classIndex])

        # in case of address-only we return string not tuple
        if len(item) == 1:
            ret.append(item[0])
        else:
            ret.append(tuple(item))
    return ret


def find_service(name=None, uuid=None, address=None):
    if address is not None:
        addresses = [address]
    else:
        addresses = discover_devices(lookup_names=False)

    results = []

    for address in addresses:
        # print "[DEBUG] Browsing services on %s..." % (addr)

        dresults = lightblue.findservices(addr=address, name=name)

        for tup in dresults:
            service = {}

            # LightBlue performs a service discovery and returns the found
            # services as a list of (device-address, service-port,
            # service-name) tuples.
            service["host"] = tup[0]
            service["port"] = tup[1]
            service["name"] = tup[2]

            # Add extra keys for compatibility with PyBluez API.
            service["description"] = None
            service["provider"] = None
            service["protocol"] = None
            service["service-classes"] = []
            service["profiles"] = []
            service["service-id"] = None

            results.append(service)

    return results

class BluetoothSocket:

    def __init__(self, proto=RFCOMM, _sock=None):
        if _sock is None:
            _sock = lightblue.socket()
        self._sock = _sock

        if proto != RFCOMM:
            # name the protocol
            raise NotImplementedError("Not supported protocol")
        self._proto = lightblue.RFCOMM
        self._addrport = None

    def _getport(self):
        return self._addrport[1]

    def bind(self, addrport):
        self._addrport = addrport
        return self._sock.bind(addrport)

    def listen(self, backlog):
        return self._sock.listen(backlog)

    def accept(self):
        return self._sock.accept()

    def connect(self, addrport):
        return self._sock.connect(addrport)

    def send(self, data):
        return self._sock.send(data)

    def recv(self, numbytes):
        return self._sock.recv(numbytes)

    def close(self):
        return self._sock.close()

    def getsockname(self):
        return self._sock.getsockname()

    def setblocking(self, blocking):
        return self._sock.setblocking(blocking)

    def settimeout(self, timeout):
        return self._sock.settimeout(timeout)

    def gettimeout(self):
        return self._sock.gettimeout()

    def fileno(self):
        return self._sock.fileno()

    def dup(self):
        return BluetoothSocket(self._proto, self._sock)

    def makefile(self, mode, bufsize):
        return self.makefile(mode, bufsize)

def discover_devices (duration=8, flush_cache=True, lookup_names=False,
                      lookup_class=False, device_id=-1):
    #this is order of items in C-code
    btAddresIndex = 0
    namesIndex = 1
    classIndex = 2

    try:
        devices = bt.discover_devices(duration=duration, flush_cache=flush_cache)
    except OSError:
        return []
    ret = list()
    for device in devices:
        item = [device[btAddresIndex],]
        if lookup_names:
            item.append(device[namesIndex])
        if lookup_class:
            item.append(device[classIndex])

        if len(item) == 1: # in case of address-only we return string not tuple
            ret.append(item[0])
        else:
            ret.append(tuple(i for i in item))
    return ret


class BluetoothSocket:
    def __init__(self, proto=RFCOMM, sockfd=None):
        if proto not in [RFCOMM]:
            raise ValueError("invalid protocol")

        if sockfd:
            self._sockfd = sockfd
        else:
            self._sockfd = bt.socket(bt.SOCK_STREAM, bt.BTHPROTO_RFCOMM)
        self._proto = proto

        # used by advertise_service and stop_advertising
        self._sdp_handle = None
        self._raw_sdp_record = None

        # used to track if in blocking or non-blocking mode (FIONBIO appears
        # write only)
        self._blocking = True
        self._timeout = False

    @property
    def family(self):
        return bt.AF_BTH

    @property
    def type(self):
        return bt.SOCK_STREAM

    @property
    def proto(self):
        return bt.BTHPROTO_RFCOMM

    def bind(self, addrport):
        if self._proto == RFCOMM:
            addr, port = addrport

            if port == 0: port = bt.BT_PORT_ANY
            bt.bind(self._sockfd, addr, port)

    def listen(self, backlog):
        bt.listen(self._sockfd, backlog)

    def accept(self):
        clientfd, addr, port = bt.accept(self._sockfd)
        client = BluetoothSocket(self._proto, sockfd=clientfd)
        return client, (addr, port)

    def connect(self, addrport):
        addr, port = addrport
        bt.connect(self._sockfd, addr, port)

    def send(self, data):
        return bt.send(self._sockfd, data)

    def recv(self, numbytes):
        return bt.recv(self._sockfd, numbytes)

    def close(self):
        return bt.close(self._sockfd)

    def getsockname(self):
        return bt.getsockname(self._sockfd)

    def getpeername(self):
        return bt.getpeername(self._sockfd)

    getpeername.__doc__ = bt.getpeername.__doc__

    def setblocking(self, blocking):
        bt.setblocking(self._sockfd, blocking)
        self._blocking = blocking

    def settimeout(self, timeout):
        if timeout < 0: raise ValueError("invalid timeout")

        if timeout == 0:
            self.setblocking(False)
        else:
            self.setblocking(True)

        bt.settimeout(self._sockfd, timeout)
        self._timeout = timeout

    def gettimeout(self):
        if self._blocking and not self._timeout: return None
        return bt.gettimeout(self._sockfd)

    def fileno(self):
        return self._sockfd

    def dup(self):
        return BluetoothSocket(self._proto, sockfd=bt.dup(self._sockfd))

    def makefile(self):
        # TODO
        raise Exception("Not yet implemented")


def advertise_service(sock, name, service_id="", service_classes=[], \
                      profiles=[], provider="", description="", protocols=[]):
    if service_id != "" and not is_valid_uuid(service_id):
        raise ValueError("invalid UUID specified for service_id")
    for uuid in service_classes:
        if not is_valid_uuid(uuid):
            raise ValueError("invalid UUID specified in service_classes")
    for uuid, version in profiles:
        if not is_valid_uuid(uuid) or version < 0 or version > 0xFFFF:
            raise ValueError("Invalid Profile Descriptor")
    for uuid in protocols:
        if not is_valid_uuid(uuid):
            raise ValueError("invalid UUID specified in protocols")

    if sock._raw_sdp_record is not None:
        raise OSError("service already advertised")

    avpairs = []

    # service UUID
    if len(service_id) > 0:
        avpairs.append(("UInt16", SERVICE_ID_ATTRID))
        avpairs.append(("UUID", service_id))

    # service class list
    if len(service_classes) > 0:
        seq = [("UUID", svc_class) for svc_class in service_classes]
        avpairs.append(("UInt16", SERVICE_CLASS_ID_LIST_ATTRID))
        avpairs.append(("ElemSeq", seq))

    # set protocol and port information
    assert sock._proto == RFCOMM
    addr, port = sock.getsockname()
    avpairs.append(("UInt16", PROTOCOL_DESCRIPTOR_LIST_ATTRID))
    l2cap_pd = ("ElemSeq", (("UUID", L2CAP_UUID),))
    rfcomm_pd = ("ElemSeq", (("UUID", RFCOMM_UUID), ("UInt8", port)))
    proto_list = [l2cap_pd, rfcomm_pd]
    for proto_uuid in protocols:
        proto_list.append(("ElemSeq", (("UUID", proto_uuid),)))
    avpairs.append(("ElemSeq", proto_list))

    # make the service publicly browseable
    avpairs.append(("UInt16", BROWSE_GROUP_LIST_ATTRID))
    avpairs.append(("ElemSeq", (("UUID", PUBLIC_BROWSE_GROUP),)))

    # profile descriptor list
    if len(profiles) > 0:
        seq = [("ElemSeq", (("UUID", uuid), ("UInt16", version))) \
               for uuid, version in profiles]
        avpairs.append(("UInt16",
                        BLUETOOTH_PROFILE_DESCRIPTOR_LIST_ATTRID))
        avpairs.append(("ElemSeq", seq))

    # service name
    avpairs.append(("UInt16", SERVICE_NAME_ATTRID))
    avpairs.append(("String", name))

    # service description
    if len(description) > 0:
        avpairs.append(("UInt16", SERVICE_DESCRIPTION_ATTRID))
        avpairs.append(("String", description))

    # service provider
    if len(provider) > 0:
        avpairs.append(("UInt16", PROVIDER_NAME_ATTRID))
        avpairs.append(("String", provider))

    sock._raw_sdp_record = sdp_make_data_element("ElemSeq", avpairs)
    #    pr = sdp_parse_raw_record (sock._raw_sdp_record)
    #    for attrid, val in pr.items ():
    #        print "%5s: %s" % (attrid, val)
    #    print binascii.hexlify (sock._raw_sdp_record)
    #    print repr (sock._raw_sdp_record)

    sock._sdp_handle = bt.set_service_raw(sock._raw_sdp_record, True)


def stop_advertising(sock):
    if sock._raw_sdp_record is None:
        raise OSError("service isn't advertised, " \
                      "but trying to un-advertise")
    bt.set_service_raw(sock._raw_sdp_record, False, sock._sdp_handle)
    sock._raw_sdp_record = None
    sock._sdp_handle = None


def find_service(name=None, uuid=None, address=None):
    if address is not None:
        addresses = [address]
    else:
        addresses = discover_devices(lookup_names=False)

    results = []

    for addr in addresses:
        uuidstr = uuid or PUBLIC_BROWSE_GROUP
        if not is_valid_uuid(uuidstr): raise ValueError("invalid UUID")

        uuidstr = to_full_uuid(uuidstr)

        dresults = bt.find_service(addr, uuidstr)

        for dict in dresults:
            raw = dict["rawrecord"]

            record = sdp_parse_raw_record(raw)

            if SERVICE_CLASS_ID_LIST_ATTRID in record:
                svc_class_id_list = [t[1] for t in \
                                     record[SERVICE_CLASS_ID_LIST_ATTRID]]
                dict["service-classes"] = svc_class_id_list
            else:
                dict["services-classes"] = []

            if BLUETOOTH_PROFILE_DESCRIPTOR_LIST_ATTRID in record:
                pdl = []
                for profile_desc in \
                        record[BLUETOOTH_PROFILE_DESCRIPTOR_LIST_ATTRID]:
                    uuidpair, versionpair = profile_desc[1]
                    pdl.append((uuidpair[1], versionpair[1]))
                dict["profiles"] = pdl
            else:
                dict["profiles"] = []

            dict["provider"] = record.get(PROVIDER_NAME_ATTRID, None)

            dict["service-id"] = record.get(SERVICE_ID_ATTRID, None)

            # XXX the C version is buggy (retrieves an extra byte or two),
            # so get the service name here even though it may have already
            # been set
            dict["name"] = record.get(SERVICE_NAME_ATTRID, None)

            dict["handle"] = record.get(SERVICE_RECORD_HANDLE_ATTRID, None)

        #        if LANGUAGE_BASE_ATTRID_LIST_ATTRID in record:
        #            for triple in record[LANGUAGE_BASE_ATTRID_LIST_ATTRID]:
        #                code_ISO639, encoding, base_offset = triple
        #
        #        if SERVICE_DESCRIPTION_ATTRID in record:
        #            service_description = record[SERVICE_DESCRIPTION_ATTRID]

        if name is None:
            results.extend(dresults)
        else:
            results.extend([d for d in dresults if d["name"] == name])
    return results


class DocumentationProvider:
    def __init__(self, is_async: bool) -> None:
        self.is_async = is_async
        self.api: Any = {}
        self.links: Dict[str, str] = {}
        self.printed_entries: List[str] = []
        process_output = subprocess.run(
            ["python", "-m", "playwright", "print-api-json"],
            check=True,
            capture_output=True,
        )
        self.api = json.loads(process_output.stdout)
        self.errors: Set[str] = set()
        self._patch_case()

    def _patch_case(self) -> None:
        self.classes = {}
        for clazz in self.api:
            if not works_for_python(clazz):
                continue
            members = {}
            self.classes[clazz["name"]] = clazz
            events = []
            for member in clazz["members"]:
                if not works_for_python(member):
                    continue
                member_name = member["name"]
                new_name = name_or_alias(member)
                self._add_link(member["kind"], clazz["name"], member_name, new_name)

                if member["kind"] == "event":
                    events.append(member)
                else:
                    new_name = to_snake_case(new_name)
                    member["name"] = new_name
                    members[new_name] = member
                apply_type_or_override(member)

                if "args" in member:
                    args = {}
                    for arg in member["args"]:
                        if not works_for_python(arg):
                            continue
                        if arg["name"] == "options":
                            for option in arg["type"]["properties"]:
                                if not works_for_python(option):
                                    continue
                                option = self_or_override(option)
                                option_name = to_snake_case(name_or_alias(option))
                                option["name"] = option_name
                                option["required"] = False
                                args[option_name] = option
                        else:
                            arg = self_or_override(arg)
                            arg_name = to_snake_case(name_or_alias(arg))
                            arg["name"] = arg_name
                            args[arg_name] = arg

                    member["args"] = args

            clazz["members"] = members
            clazz["events"] = events

    def _add_link(self, kind: str, clazz: str, member: str, alias: str) -> None:
        match = re.match(r"(JS|CDP|[A-Z])([^.]+)", clazz)
        if not match:
            raise Exception("Invalid class " + clazz)
        var_name = to_snake_case(f"{match.group(1).lower()}{match.group(2)}")
        new_name = to_snake_case(alias)
        if kind == "event":
            new_name = new_name.lower()
            self.links[
                f"[`event: {clazz}.{member}`]"
            ] = f"`{var_name}.on('{new_name}')`"
        elif kind == "property":
            self.links[f"[`property: {clazz}.{member}`]"] = f"`{var_name}.{new_name}`"
        else:
            self.links[f"[`method: {clazz}.{member}`]"] = f"`{var_name}.{new_name}()`"

    def print_entry(
        self,
        class_name: str,
        method_name: str,
        signature: Dict[str, Any] = None,
        is_property: bool = False,
    ) -> None:
        if class_name in ["BindingCall"] or method_name in [
            "pid",
        ]:
            return
        original_method_name = method_name
        self.printed_entries.append(f"{class_name}.{method_name}")
        clazz = self.classes[class_name]
        method = clazz["members"].get(method_name)
        if not method and "extends" in clazz:
            superclass = self.classes.get(clazz["extends"])
            if superclass:
                method = superclass["members"].get(method_name)
        fqname = f"{class_name}.{method_name}"

        if not method:
            self.errors.add(f"Method not documented: {fqname}")
            return

        doc_is_property = (
            not method.get("async") and not len(method["args"]) and "type" in method
        )
        if method["name"].startswith("is_") or method["name"].startswith("as_"):
            doc_is_property = False
        if doc_is_property != is_property:
            self.errors.add(f"Method vs property mismatch: {fqname}")
            return

        indent = " " * 8
        print(f'{indent}"""{class_name}.{to_snake_case(original_method_name)}')
        if method.get("comment"):
            print(f"{indent}{self.beautify_method_comment(method['comment'], indent)}")
        signature_no_return = {**signature} if signature else None
        if signature_no_return and "return" in signature_no_return:
            del signature_no_return["return"]

        # Collect a list of all names, flatten options.
        args = method["args"]
        if signature and signature_no_return:
            print("")
            print("        Parameters")
            print("        ----------")
            for [name, value] in signature.items():
                name = to_snake_case(name)
                if name == "return":
                    continue
                original_name = name
                doc_value = args.get(name)
                if name in args:
                    del args[name]
                if not doc_value:
                    self.errors.add(f"Parameter not documented: {fqname}({name}=)")
                else:
                    code_type = self.serialize_python_type(value, "in")

                    print(f"{indent}{to_snake_case(original_name)} : {code_type}")
                    if doc_value.get("comment"):
                        print(
                            f"{indent}    {self.indent_paragraph(self.render_links(doc_value['comment']), f'{indent}    ')}"
                        )
                    if doc_value.get("deprecated"):
                        print(
                            f"{indent}    Deprecated: {self.render_links(doc_value['deprecated'])}"
                        )
                    self.compare_types(code_type, doc_value, f"{fqname}({name}=)", "in")
        if (
            signature
            and "return" in signature
            and str(signature["return"]) != "<class 'NoneType'>"
        ):
            value = signature["return"]
            doc_value = method
            self.compare_types(value, doc_value, f"{fqname}(return=)", "out")
            print("")
            print("        Returns")
            print("        -------")
            print(f"        {self.serialize_python_type(value, 'out')}")
        print(f'{indent}"""')

        for name in args:
            if args[name].get("deprecated"):
                continue
            self.errors.add(
                f"Parameter not implemented: {class_name}.{method_name}({name}=)"
            )

    def print_events(self, class_name: str) -> None:
        clazz = self.classes[class_name]
        events = clazz["events"]
        if events:
            doc = []
            for event_type in ["on", "once"]:
                for event in events:
                    return_type = (
                        "typing.Union[typing.Awaitable[None], None]"
                        if self.is_async
                        else "None"
                    )
                    func_arg = self.serialize_doc_type(event["type"], "")
                    if func_arg.startswith("{"):
                        func_arg = "typing.Dict"
                    if "Union[" in func_arg:
                        func_arg = func_arg.replace("Union[", "typing.Union[")
                    if len(events) > 1:
                        doc.append("    @typing.overload")
                    impl = ""
                    if len(events) == 1:
                        impl = f"        return super().{event_type}(event=event,f=f)"
                    doc.append(
                        f"    def {event_type}(self, event: Literal['{event['name'].lower()}'], f: typing.Callable[['{func_arg}'], '{return_type}']) -> None:"
                    )
                    doc.append(
                        f'        """{self.beautify_method_comment(event["comment"], " " * 8)}"""'
                    )
                    doc.append(impl)
                if len(events) > 1:
                    doc.append(
                        f"    def {event_type}(self, event: str, f: typing.Callable[...,{return_type}]) -> None:"
                    )
                    doc.append(f"        return super().{event_type}(event=event,f=f)")
            print("\n".join(doc))

    def indent_paragraph(self, p: str, indent: str) -> str:
        lines = p.split("\n")
        result = [lines[0]]
        for line in lines[1:]:
            result.append(indent + line)
        return "\n".join(result)

    def beautify_method_comment(self, comment: str, indent: str) -> str:
        comment = self.filter_out_redudant_python_code_snippets(comment)
        comment = comment.replace("\\", "\\\\")
        comment = comment.replace('"', '\\"')
        lines = comment.split("\n")
        result = []
        skip_example = False
        last_was_blank = True
        for line in lines:
            if not line.strip():
                last_was_blank = True
                continue
            match = re.match(r"\s*```(.+)", line)
            if match:
                lang = match[1]
                if lang in ["html", "yml", "sh", "py", "python"]:
                    skip_example = False
                elif lang == "python " + ("async" if self.is_async else "sync"):
                    skip_example = False
                    line = "```py"
                else:
                    skip_example = True
            if not skip_example:
                if last_was_blank:
                    last_was_blank = False
                    result.append("")
                result.append(self.render_links(line))
            if skip_example and line.strip() == "```":
                skip_example = False
        comment = self.indent_paragraph("\n".join(result), indent)
        return self.resolve_playwright_dev_links(comment)

    def filter_out_redudant_python_code_snippets(self, comment: str) -> str:
        groups = []
        current_group = []
        lines = comment.split("\n")
        start_pos = None
        for i in range(len(lines)):
            line = lines[i].strip()
            if line.startswith("```py"):
                start_pos = i
            elif line == "```" and start_pos is not None:
                current_group.append((start_pos, i))
                start_pos = None
            elif (
                (line.startswith("```") or i == len(lines) - 1)
                and start_pos is None
                and len(current_group) == 2
            ):
                groups.append(current_group)
                current_group = []
        groups.reverse()
        for first_pos, second_pos in groups:
            # flake8: noqa: E203
            second_snippet_is_async = "await" in lines[second_pos[0] : second_pos[1]]
            if second_snippet_is_async == self.is_async:
                # flake8: noqa: E203
                del lines[first_pos[0] : first_pos[1] + 1]
            else:
                # flake8: noqa: E203
                del lines[second_pos[0] : second_pos[1] + 1]
        return "\n".join(lines)

    def resolve_playwright_dev_links(self, comment: str) -> str:
        def replace_callback(m: re.Match) -> str:
            link_text = m.group(1)
            link_href = m.group(2)
            resolved = urljoin(
                "https://playwright.dev/python/docs/api/", link_href.replace(".md", "")
            )
            return f"[{link_text}]({resolved})"

        # matches against internal markdown links which start with '.'/'..'
        # e.g. [Playwright](./class-foobar.md)
        return re.sub(r"\[([^\]]+)\]\((\.[^\)]+)\)", replace_callback, comment)

    def render_links(self, comment: str) -> str:
        for [old, new] in self.links.items():
            comment = comment.replace(old, new)
        return comment

    def make_optional(self, text: str) -> str:
        if text.startswith("Union["):
            if text.endswith("None]"):
                return text
            return text[:-1] + ", None]"
        return f"Union[{text}, None]"

    def compare_types(
        self, value: Any, doc_value: Any, fqname: str, direction: str
    ) -> None:
        if "(arg=)" in fqname or "(pageFunction=)" in fqname:
            return
        code_type = self.serialize_python_type(value, direction)
        doc_type = self.serialize_doc_type(doc_value["type"], direction)
        if not doc_value["required"]:
            doc_type = self.make_optional(doc_type)

        if doc_type != code_type:
            self.errors.add(
                f"Parameter type mismatch in {fqname}: documented as {doc_type}, code has {code_type}"
            )

    def serialize_python_type(self, value: Any, direction: str) -> str:
        str_value = str(value)
        if isinstance(value, list):
            return f"[{', '.join(list(map(lambda a: self.serialize_python_type(a, direction), value)))}]"
        if str_value == "<class 'playwright._impl._errors.Error'>":
            return "Error"
        if str_value == "<class 'NoneType'>":
            return "None"
        match = re.match(r"^<class '((?:pathlib\.)?\w+)'>$", str_value)
        if match:
            return match.group(1)
        match = re.match(
            r"playwright._impl._event_context_manager.EventContextManagerImpl\[playwright._impl.[^.]+.(.*)\]",
            str_value,
        )
        if match:
            return "EventContextManager[" + match.group(1) + "]"
        match = re.match(r"^<class 'playwright\._impl\.[\w_]+\.([^']+)'>$", str_value)
        if match and "_api_structures" not in str_value and "_errors" not in str_value:
            if match.group(1) == "EventContextManagerImpl":
                return "EventContextManager"
            return match.group(1)

        match = re.match(r"^typing\.(\w+)$", str_value)
        if match:
            return match.group(1)

        origin = get_origin(value)
        args = get_args(value)
        hints = None
        try:
            hints = get_type_hints(value)
        except Exception:
            pass
        if hints:
            signature: List[str] = []
            for [name, value] in hints.items():
                signature.append(
                    f"{name}: {self.serialize_python_type(value, direction)}"
                )
            return f"{{{', '.join(signature)}}}"
        if origin == Union:
            args = get_args(value)
            if len(args) == 2 and str(args[1]) == "<class 'NoneType'>":
                return self.make_optional(
                    self.serialize_python_type(args[0], direction)
                )
            ll = list(map(lambda a: self.serialize_python_type(a, direction), args))
            ll.sort(key=lambda item: "}" if item == "None" else item)
            return f"Union[{', '.join(ll)}]"
        if str(origin) == "<class 'dict'>":
            args = get_args(value)
            return f"Dict[{', '.join(list(map(lambda a: self.serialize_python_type(a, direction), args)))}]"
        if str(origin) == "<class 'collections.abc.Sequence'>":
            args = get_args(value)
            return f"Sequence[{', '.join(list(map(lambda a: self.serialize_python_type(a, direction), args)))}]"
        if str(origin) == "<class 'list'>":
            args = get_args(value)
            list_type = "Sequence" if direction == "in" else "List"
            return f"{list_type}[{', '.join(list(map(lambda a: self.serialize_python_type(a, direction), args)))}]"
        if str(origin) == "<class 'collections.abc.Callable'>":
            args = get_args(value)
            return f"Callable[{', '.join(list(map(lambda a: self.serialize_python_type(a, direction), args)))}]"
        if str(origin) == "<class 're.Pattern'>":
            return "Pattern[str]"
        if str(origin) == "typing.Literal":
            args = get_args(value)
            if len(args) == 1:
                return '"' + self.serialize_python_type(args[0], direction) + '"'
            body = ", ".join(
                list(
                    map(
                        lambda a: '"' + self.serialize_python_type(a, direction) + '"',
                        args,
                    )
                )
            )
            return f"Union[{body}]"
        return str_value

    def serialize_doc_type(self, type: Any, direction: str) -> str:
        result = self.inner_serialize_doc_type(type, direction)
        return result

    def inner_serialize_doc_type(self, type: Any, direction: str) -> str:
        if type["name"] == "Promise":
            type = type["templates"][0]

        if "union" in type:
            ll = [self.serialize_doc_type(t, direction) for t in type["union"]]
            ll.sort(key=lambda item: "}" if item == "None" else item)
            for i in range(len(ll)):
                if ll[i].startswith("Union["):
                    ll[i] = ll[i][6:-1]
            return f"Union[{', '.join(ll)}]"

        type_name = type["name"]
        if type_name == "path":
            if direction == "in":
                return "Union[pathlib.Path, str]"
            else:
                return "pathlib.Path"

        if type_name == "function" and "args" not in type:
            return "Callable"

        if type_name == "function":
            return_type = "Any"
            if type.get("returnType"):
                return_type = self.serialize_doc_type(type["returnType"], direction)
            return f"Callable[[{', '.join(self.serialize_doc_type(t, direction) for t in type['args'])}], {return_type}]"

        if "templates" in type:
            base = type_name
            if type_name == "Array":
                base = "Sequence" if direction == "in" else "List"
            if type_name == "Object" or type_name == "Map":
                base = "Dict"
            return f"{base}[{', '.join(self.serialize_doc_type(t, direction) for t in type['templates'])}]"

        if type_name == "Object" and "properties" in type:
            items = []
            for p in type["properties"]:
                items.append(
                    (p["name"])
                    + ": "
                    + (
                        self.serialize_doc_type(p["type"], direction)
                        if p["required"]
                        else self.make_optional(
                            self.serialize_doc_type(p["type"], direction)
                        )
                    )
                )
            return f"{{{', '.join(items)}}}"
        if type_name == "boolean":
            return "bool"
        if type_name.lower() == "string":
            return "str"
        if type_name == "any" or type_name == "Serializable":
            return "Any"
        if type_name == "Object":
            return "Dict"
        if type_name == "Function":
            return "Callable"
        if type_name == "Buffer" or type_name == "ReadStream":
            return "bytes"
        if type_name == "URL":
            return "str"
        if type_name == "RegExp":
            return "Pattern[str]"
        if type_name == "null":
            return "None"
        if type_name == "EvaluationArgument":
            return "Dict"
        return type["name"]

    def print_remainder(self) -> None:
        for [class_name, clazz] in self.classes.items():
            for [member_name, member] in clazz["members"].items():
                if member.get("deprecated"):
                    continue
                if class_name in ["Error"]:
                    continue
                entry = f"{class_name}.{member_name}"
                if entry not in self.printed_entries:
                    self.errors.add(f"Method not implemented: {entry}")

        with open("scripts/expected_api_mismatch.txt") as f:
            for line in f.readlines():
                sline = line.strip()
                if not len(sline) or sline.startswith("#"):
                    continue
                if sline in self.errors:
                    self.errors.remove(sline)
                else:
                    print("No longer there: " + sline, file=stderr)

        if len(self.errors) > 0:
            for error in self.errors:
                print(error, file=stderr)
            exit(1)


def process_type(value: Any, param: bool = False) -> str:
    value = str(value)
    value = re.sub(r"<class '([^']+)'>", r"\1", value)
    value = re.sub(r"NoneType", "None", value)
    value = re.sub(r"playwright\._impl\._api_structures.([\w]+)", r"\1", value)
    value = re.sub(r"playwright\._impl\.[\w]+\.([\w]+)", r'"\1"', value)
    value = re.sub(r"typing.Literal", "Literal", value)
    if param:
        value = re.sub(r"^typing.Union\[([^,]+), None\]$", r"\1 = None", value)
        value = re.sub(
            r"typing.Union\[(Literal\[[^\]]+\]), None\]", r"\1 = None", value
        )
        value = re.sub(
            r"^typing.Union\[(.+), None\]$", r"typing.Union[\1] = None", value
        )
        value = re.sub(
            r"^typing.Optional\[(.+)\]$", r"typing.Optional[\1] = None", value
        )
        if not re.match(r"typing.Optional\[.*\] = None", value):
            value = re.sub(r"(.*) = None", r"typing.Optional[\1] = None", value)
    return value


def signature(func: FunctionType, indent: int) -> str:
    hints = get_type_hints(func, globals())
    tokens = ["self"]
    split = ",\n" + " " * indent

    saw_optional = False
    for [name, value] in hints.items():
        if name == "return":
            continue
        positional_exception = is_positional_exception(f"{func.__name__}.{name}")
        if saw_optional and positional_exception:
            raise Exception(
                "Positional exception is not first in the list "
                + f"{func.__name__}.{name}"
            )
        processed = process_type(value, True)
        if (
            not positional_exception
            and not saw_optional
            and processed.startswith("typing.Optional")
        ):
            saw_optional = True
            tokens.append("*")
        tokens.append(f"{to_snake_case(name)}: {processed}")
    return split.join(tokens)

def arguments(func: FunctionType, indent: int) -> str:
    hints = get_type_hints(func, globals())
    tokens = []
    split = ",\n" + " " * indent
    for [name, value] in hints.items():
        value_str = str(value)
        if name == "return":
            continue
        assert (
            "_" not in name
        ), f"Underscore in impl classes is not allowed, use camel case, func={func}, name={name}"
        if "Callable" in value_str:
            tokens.append(f"{name}=self._wrap_handler({to_snake_case(name)})")
        elif (
            "typing.Any" in value_str
            or "typing.Dict" in value_str
            or "typing.Sequence" in value_str
            or "Handle" in value_str
        ):
            tokens.append(f"{name}=mapping.to_impl({to_snake_case(name)})")
        elif (
            re.match(r"<class 'playwright\._impl\.[\w]+\.[\w]+", value_str)
            and "_api_structures" not in value_str
        ):
            tokens.append(f"{name}={to_snake_case(name)}._impl_obj")
        elif (
            re.match(r"typing\.Optional\[playwright\._impl\.[\w]+\.[\w]+\]", value_str)
            and "_api_structures" not in value_str
        ):
            tokens.append(
                f"{name}={to_snake_case(name)}._impl_obj if {to_snake_case(name)} else None"
            )
        else:
            tokens.append(f"{name}={to_snake_case(name)}")
    return split.join(tokens)


def return_value(value: Any) -> List[str]:
    value_str = str(value)
    if "playwright" not in value_str:
        return ["mapping.from_maybe_impl(", ")"]
    if (
        get_origin(value) == Union
        and len(get_args(value)) == 2
        and str(get_args(value)[1]) == "<class 'NoneType'>"
    ):
        return ["mapping.from_impl_nullable(", ")"]
    if str(get_origin(value)) in [
        "<class 'list'>",
        "<class 'collections.abc.Sequence'>",
    ]:
        return ["mapping.from_impl_list(", ")"]
    if str(get_origin(value)) == "<class 'dict'>":
        return ["mapping.from_impl_dict(", ")"]
    return ["mapping.from_impl(", ")"]


def generate(t: Any) -> None:
    print("")
    class_name = short_name(t)
    base_class = t.__bases__[0].__name__
    if class_name in ["Page", "BrowserContext", "Browser"]:
        base_sync_class = "AsyncContextManager"
    elif base_class in ["ChannelOwner", "object", "AssertionsBase"]:
        base_sync_class = "AsyncBase"
    else:
        base_sync_class = base_class
    print(f"class {class_name}({base_sync_class}):")
    print("")
    documentation_provider.print_events(class_name)
    for [name, type] in get_type_hints(t, api_globals).items():
        print("")
        print("    @property")
        print(f"    def {name}(self) -> {process_type(type)}:")
        documentation_provider.print_entry(class_name, name, {"return": type}, True)
        [prefix, suffix] = return_value(type)
        prefix = "        return " + prefix + f"self._impl_obj.{name}"
        print(f"{prefix}{suffix}")
    for [name, value] in t.__dict__.items():
        if name.startswith("_"):
            continue
        if str(value).startswith("<property"):
            value = value.fget
            print("")
            print("    @property")
            print(
                f"    def {name}({signature(value, len(name) + 9)}) -> {return_type(value)}:"
            )
            documentation_provider.print_entry(
                class_name, name, get_type_hints(value, api_globals), True
            )
            [prefix, suffix] = return_value(
                get_type_hints(value, api_globals)["return"]
            )
            prefix = "        return " + prefix + f"self._impl_obj.{name}"
            print(f"{prefix}{arguments(value, len(prefix))}{suffix}")
    for [name, value] in t.__dict__.items():
        if isinstance(value, FunctionType) and "remove_listener" != name:
            # List of dunder methods to allow without docs
            allow_without_docs_methods = [
                "__getitem__",
            ]
            if name.startswith("_") and name not in allow_without_docs_methods:
                continue
            is_async = inspect.iscoroutinefunction(value)
            return_type_value = return_type(value)
            return_type_value = re.sub(r"\"([^\"]+)Impl\"", r"\1", return_type_value)
            return_type_value = return_type_value.replace(
                "EventContextManager", "AsyncEventContextManager"
            )
            print("")
            async_prefix = "async " if is_async else ""
            print(
                f"    {async_prefix}def {name}({signature(value, len(name) + 9)}) -> {return_type_value}:"
            )
            # Allow dunder methods without docs
            if name not in allow_without_docs_methods:
                documentation_provider.print_entry(
                    class_name, name, get_type_hints(value, api_globals)
                )
            if class_name in [
                "LocatorAssertions",
                "PageAssertions",
                "APIResponseAssertions",
            ]:
                print("        __tracebackhide__ = True")
            if "expect_" in name:
                print("")
                print(
                    f"        return AsyncEventContextManager(self._impl_obj.{name}({arguments(value, 12)}).future)"
                )
            else:
                [prefix, suffix] = return_value(
                    get_type_hints(value, api_globals)["return"]
                )
                if is_async:
                    prefix += "await "
                prefix = prefix + f"self._impl_obj.{name}("
                suffix = ")" + suffix
                print(
                    f"""
        return {prefix}{arguments(value, len(prefix))}{suffix}"""
                )
    print("")
    print(f"mapping.register({class_name}Impl, {class_name})")



def generate(t: Any) -> None:
    print("")
    class_name = short_name(t)
    base_class = t.__bases__[0].__name__
    if class_name in ["Page", "BrowserContext", "Browser"]:
        base_sync_class = "SyncContextManager"
    elif base_class in ["ChannelOwner", "object", "AssertionsBase"]:
        base_sync_class = "SyncBase"
    else:
        base_sync_class = base_class
    print(f"class {class_name}({base_sync_class}):")
    print("")
    documentation_provider.print_events(class_name)
    for [name, type] in get_type_hints(t, api_globals).items():
        print("")
        print("    @property")
        print(f"    def {name}(self) -> {process_type(type)}:")
        documentation_provider.print_entry(class_name, name, {"return": type}, True)
        [prefix, suffix] = return_value(type)
        prefix = "        return " + prefix + f"self._impl_obj.{name}"
        print(f"{prefix}{suffix}")
    for [name, value] in t.__dict__.items():
        if name.startswith("_"):
            continue
        if str(value).startswith("<property"):
            value = value.fget
            print("")
            print("    @property")
            print(
                f"    def {name}({signature(value, len(name) + 9)}) -> {return_type(value)}:"
            )
            documentation_provider.print_entry(
                class_name, name, get_type_hints(value, api_globals), True
            )
            [prefix, suffix] = return_value(
                get_type_hints(value, api_globals)["return"]
            )
            prefix = "        return " + prefix + f"self._impl_obj.{name}"
            print(f"{prefix}{arguments(value, len(prefix))}{suffix}")
    for [name, value] in t.__dict__.items():
        if isinstance(value, FunctionType) and "remove_listener" != name:
            # List of dunder methods to allow without docs
            allow_without_docs_methods = [
                "__getitem__",
            ]
            if name.startswith("_") and name not in allow_without_docs_methods:
                continue
            is_async = inspect.iscoroutinefunction(value)
            return_type_value = return_type(value)
            return_type_value = re.sub(r"\"([^\"]+)Impl\"", r"\1", return_type_value)
            print("")
            print(
                f"    def {name}({signature(value, len(name) + 9)}) -> {return_type_value}:"
            )
            # Allow dunder methods without docs
            if name not in allow_without_docs_methods:
                documentation_provider.print_entry(
                    class_name, name, get_type_hints(value, api_globals)
                )
            if class_name in [
                "LocatorAssertions",
                "PageAssertions",
                "APIResponseAssertions",
            ]:
                print("        __tracebackhide__ = True")
            if "expect_" in name:
                print(
                    f"        return EventContextManager(self, self._impl_obj.{name}({arguments(value, 12)}).future)"
                )
            else:
                [prefix, suffix] = return_value(
                    get_type_hints(value, api_globals)["return"]
                )
                if is_async:
                    prefix += f"self._sync(self._impl_obj.{name}("
                    suffix = "))" + suffix
                else:
                    prefix += f"self._impl_obj.{name}("
                    suffix = ")" + suffix

                print(
                    f"""
        return {prefix}{arguments(value, len(prefix))}{suffix}"""
                )
    print("")
    print(f"mapping.register({class_name}Impl, {class_name})")



def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("playwright", "Playwright")
    group.addoption(
        "--browser",
        action="append",
        default=[],
        help="Browsers which should be used. By default on all the browsers.",
    )
    group.addoption(
        "--browser-channel",
        action="store",
        default=None,
        help="Browser channel to be used.",
    )
    parser.addoption(
        "--headed",
        action="store_true",
        default=False,
        help="Run tests in headed mode.",
    )


@pytest.fixture(scope="session")
def assert_to_be_golden(browser_name: str) -> Callable[[bytes, str], None]:
    def compare(received_raw: bytes, golden_name: str) -> None:
        golden_file_path = _dirname / f"golden-{browser_name}" / golden_name
        try:
            golden_file = golden_file_path.read_bytes()
            received_image = Image.open(io.BytesIO(received_raw))
            golden_image = Image.open(io.BytesIO(golden_file))

            if golden_image.size != received_image.size:
                pytest.fail("Image size differs to golden image")
                return
            diff_pixels = pixelmatch(
                from_PIL_to_raw_data(received_image),
                from_PIL_to_raw_data(golden_image),
                golden_image.size[0],
                golden_image.size[1],
                threshold=0.2,
            )
            assert diff_pixels == 0
        except Exception:
            if os.getenv("PW_WRITE_SCREENSHOT"):
                golden_file_path.parent.mkdir(parents=True, exist_ok=True)
                golden_file_path.write_bytes(received_raw)
                print(f"Wrote {golden_file_path}")
            raise

    return compare


class RemoteServer:
    def __init__(
        self, browser_name: str, launch_server_options: Dict, tmpfile: Path
    ) -> None:
        driver_dir = Path(inspect.getfile(playwright)).parent / "driver"
        if sys.platform == "win32":
            node_executable = driver_dir / "node.exe"
        else:
            node_executable = driver_dir / "node"
        cli_js = driver_dir / "package" / "cli.js"
        tmpfile.write_text(json.dumps(launch_server_options))
        self.process = subprocess.Popen(
            [
                str(node_executable),
                str(cli_js),
                "launch-server",
                "--browser",
                browser_name,
                "--config",
                str(tmpfile),
            ],
            stdout=subprocess.PIPE,
            stderr=sys.stderr,
            cwd=driver_dir,
        )
        assert self.process.stdout
        self.ws_endpoint = self.process.stdout.readline().decode().strip()
        self.process.stdout.close()

    def kill(self) -> None:
        # Send the signal to all the process groups
        if self.process.poll() is not None:
            return
        self.process.kill()
        self.process.wait()


@pytest.fixture
def launch_server(
    browser_name: str, launch_arguments: Dict, tmp_path: Path
) -> Generator[Callable[..., RemoteServer], None, None]:
    remotes: List[RemoteServer] = []

    def _launch_server(**kwargs: Dict[str, Any]) -> RemoteServer:
        remote = RemoteServer(
            browser_name,
            {
                **launch_arguments,
                **kwargs,
            },
            tmp_path / f"settings-{len(remotes)}.json",
        )
        remotes.append(remote)
        return remote

    yield _launch_server

    for remote in remotes:
        remote.kill()

class TestServerRequest(http.Request):
    __test__ = False
    channel: "TestServerHTTPChannel"
    post_body: Optional[bytes] = None

    def process(self) -> None:
        server = self.channel.factory.server_instance
        if self.content:
            self.post_body = self.content.read()
            self.content.seek(0, 0)
        else:
            self.post_body = None
        uri = urlparse(self.uri.decode())
        path = uri.path

        request_subscriber = server.request_subscribers.get(path)
        if request_subscriber:
            request_subscriber._loop.call_soon_threadsafe(
                request_subscriber.set_result, self
            )
            server.request_subscribers.pop(path)

        if server.auth.get(path):
            authorization_header = self.requestHeaders.getRawHeaders("authorization")
            creds_correct = False
            if authorization_header:
                creds_correct = server.auth.get(path) == (
                    self.getUser().decode(),
                    self.getPassword().decode(),
                )
            if not creds_correct:
                self.setHeader(b"www-authenticate", 'Basic realm="Secure Area"')
                self.setResponseCode(HTTPStatus.UNAUTHORIZED)
                self.finish()
                return
        if server.csp.get(path):
            self.setHeader(b"Content-Security-Policy", server.csp[path])
        if server.routes.get(path):
            server.routes[path](self)
            return
        file_content = None
        try:
            file_content = (server.static_path / path[1:]).read_bytes()
            content_type = mimetypes.guess_type(path)[0]
            if content_type and content_type.startswith("text/"):
                content_type += "; charset=utf-8"
            self.setHeader(b"Content-Type", content_type)
            self.setHeader(b"Cache-Control", "no-cache, no-store")
            if path in server.gzip_routes:
                self.setHeader("Content-Encoding", "gzip")
                self.write(gzip.compress(file_content))
            else:
                self.setHeader(b"Content-Length", str(len(file_content)))
                self.write(file_content)
            self.setResponseCode(HTTPStatus.OK)
        except (FileNotFoundError, IsADirectoryError, PermissionError):
            self.setResponseCode(HTTPStatus.NOT_FOUND)
        self.finish()


class TestServerHTTPChannel(http.HTTPChannel):
    factory: "TestServerFactory"
    requestFactory = TestServerRequest


class TestServerFactory(http.HTTPFactory):
    server_instance: "Server"
    protocol = TestServerHTTPChannel


class Server:
    protocol = "http"

    def __init__(self) -> None:
        self.PORT = find_free_port()
        self.EMPTY_PAGE = f"{self.protocol}://localhost:{self.PORT}/empty.html"
        self.PREFIX = f"{self.protocol}://localhost:{self.PORT}"
        self.CROSS_PROCESS_PREFIX = f"{self.protocol}://127.0.0.1:{self.PORT}"
        # On Windows, this list can be empty, reporting text/plain for scripts.
        mimetypes.add_type("text/html", ".html")
        mimetypes.add_type("text/css", ".css")
        mimetypes.add_type("application/javascript", ".js")
        mimetypes.add_type("image/png", ".png")
        mimetypes.add_type("font/woff2", ".woff2")

    def __repr__(self) -> str:
        return self.PREFIX

    @abc.abstractmethod
    def listen(self, factory: TestServerFactory) -> None:
        pass

    def start(self) -> None:
        request_subscribers: Dict[str, asyncio.Future] = {}
        auth: Dict[str, Tuple[str, str]] = {}
        csp: Dict[str, str] = {}
        routes: Dict[str, Callable[[TestServerRequest], Any]] = {}
        gzip_routes: Set[str] = set()
        self.request_subscribers = request_subscribers
        self.auth = auth
        self.csp = csp
        self.routes = routes
        self.gzip_routes = gzip_routes
        self.static_path = _dirname / "assets"
        factory = TestServerFactory()
        factory.server_instance = self
        self.listen(factory)

    async def wait_for_request(self, path: str) -> TestServerRequest:
        if path in self.request_subscribers:
            return await self.request_subscribers[path]
        future: asyncio.Future["TestServerRequest"] = asyncio.Future()
        self.request_subscribers[path] = future
        return await future

    @contextlib.contextmanager
    def expect_request(
        self, path: str
    ) -> Generator[ExpectResponse[TestServerRequest], None, None]:
        future = asyncio.create_task(self.wait_for_request(path))

        cb_wrapper: ExpectResponse[TestServerRequest] = ExpectResponse()

        def done_cb(task: asyncio.Task) -> None:
            cb_wrapper._value = future.result()

        future.add_done_callback(done_cb)
        yield cb_wrapper

    def set_auth(self, path: str, username: str, password: str) -> None:
        self.auth[path] = (username, password)

    def set_csp(self, path: str, value: str) -> None:
        self.csp[path] = value

    def reset(self) -> None:
        self.request_subscribers.clear()
        self.auth.clear()
        self.csp.clear()
        self.gzip_routes.clear()
        self.routes.clear()

    def set_route(
        self, path: str, callback: Callable[[TestServerRequest], Any]
    ) -> None:
        self.routes[path] = callback

    def enable_gzip(self, path: str) -> None:
        self.gzip_routes.add(path)

    def set_redirect(self, from_: str, to: str) -> None:
        def handle_redirect(request: http.Request) -> None:
            request.setResponseCode(HTTPStatus.FOUND)
            request.setHeader("location", to)
            request.finish()

        self.set_route(from_, handle_redirect)


class HTTPServer(Server):
    def listen(self, factory: http.HTTPFactory) -> None:
        reactor.listenTCP(self.PORT, factory, interface="127.0.0.1")
        try:
            reactor.listenTCP(self.PORT, factory, interface="::1")
        except Exception:
            pass


class HTTPSServer(Server):
    protocol = "https"

    def listen(self, factory: http.HTTPFactory) -> None:
        cert = ssl.PrivateCertificate.fromCertificateAndKeyPair(
            ssl.Certificate.loadPEM(
                (_dirname / "testserver" / "cert.pem").read_bytes()
            ),
            ssl.KeyPair.load(
                (_dirname / "testserver" / "key.pem").read_bytes(), crypto.FILETYPE_PEM
            ),
        )
        contextFactory = cert.options()
        reactor.listenSSL(self.PORT, factory, contextFactory, interface="127.0.0.1")
        try:
            reactor.listenSSL(self.PORT, factory, contextFactory, interface="::1")
        except Exception:
            pass


class WebSocketServerServer(WebSocketServerProtocol):
    def __init__(self) -> None:
        super().__init__()
        self.PORT = find_free_port()

    def start(self) -> None:
        ws = WebSocketServerFactory("ws://127.0.0.1:" + str(self.PORT))
        ws.protocol = WebSocketProtocol
        reactor.listenTCP(self.PORT, ws)


class WebSocketProtocol(WebSocketServerProtocol):
    def onConnect(self, request: Any) -> None:
        pass

    def onOpen(self) -> None:
        self.sendMessage(b"incoming")

    def onMessage(self, payload: bytes, isBinary: bool) -> None:
        if payload == b"echo-bin":
            self.sendMessage(b"\x04\x02", True)
            self.sendClose()
        if payload == b"echo-text":
            self.sendMessage(b"text", False)
            self.sendClose()
        if payload == b"close":
            self.sendClose()

    def onClose(self, wasClean: Any, code: Any, reason: Any) -> None:
        pass


class TestServer:
    def __init__(self) -> None:
        self.server = HTTPServer()
        self.https_server = HTTPSServer()
        self.ws_server = WebSocketServerServer()

    def start(self) -> None:
        self.server.start()
        self.https_server.start()
        self.ws_server.start()
        self.thread = threading.Thread(
            target=lambda: reactor.run(installSignalHandlers=False)
        )
        self.thread.start()

    def stop(self) -> None:
        reactor.stop()
        self.thread.join()

    def reset(self) -> None:
        self.server.reset()
        self.https_server.reset()

def test_install(tmp_path: Path, browser_name: str) -> None:
    env_dir = tmp_path / "env"
    env = EnvBuilder(with_pip=True)
    env.create(env_dir=env_dir)
    context = env.ensure_directories(env_dir)
    root = Path(__file__).parent.parent.resolve()
    if sys.platform == "win32":
        wheelpath = list((root / "dist").glob("playwright*win_amd64*.whl"))[0]
    elif sys.platform == "linux":
        wheelpath = list((root / "dist").glob("playwright*manylinux1*.whl"))[0]
    elif sys.platform == "darwin":
        wheelpath = list((root / "dist").glob("playwright*macosx_*.whl"))[0]
    subprocess.check_output(
        [
            context.env_exe,
            "-m",
            "pip",
            "install",
            str(wheelpath),
        ]
    )
    environ = os.environ.copy()
    environ["PLAYWRIGHT_BROWSERS_PATH"] = str(tmp_path)
    subprocess.check_output(
        [context.env_exe, "-m", "playwright", "install", browser_name], env=environ
    )
    shutil.copyfile(root / "tests" / "assets" / "client.py", tmp_path / "main.py")
    subprocess.check_output(
        [context.env_exe, str(tmp_path / "main.py"), browser_name], env=environ
    )
    assert (tmp_path / f"{browser_name}.png").exists()

def parse_trace(path: Path) -> Tuple[Dict[str, bytes], List[Any]]:
    resources: Dict[str, bytes] = {}
    with zipfile.ZipFile(path, "r") as zip:
        for name in zip.namelist():
            resources[name] = zip.read(name)
    action_map: Dict[str, Any] = {}
    events: List[Any] = []
    for name in ["trace.trace", "trace.network"]:
        for line in resources[name].decode().splitlines():
            if not line:
                continue
            event = json.loads(line)
            if event["type"] == "before":
                event["type"] = "action"
                action_map[event["callId"]] = event
                events.append(event)
            elif event["type"] == "input":
                pass
            elif event["type"] == "after":
                existing = action_map[event["callId"]]
                existing["error"] = event.get("error", None)
            else:
                events.append(event)
    return (resources, events)


def get_trace_actions(events: List[Any]) -> List[str]:
    action_events = sorted(
        list(
            filter(
                lambda e: e["type"] == "action",
                events,
            )
        ),
        key=lambda e: e["startTime"],
    )
    return [e["apiName"] for e in action_events]


TARGET_CLOSED_ERROR_MESSAGE = "Target page, context or browser has been closed"

MustType = TypeVar("MustType")


def OneHotEncoder(data, keymap=None):
    """
    OneHotEncoder takes data matrix with categorical columns and
    converts it to a sparse binary matrix.

    Returns sparse binary matrix and keymap mapping categories to indicies.
    If a keymap is supplied on input it will be used instead of creating one
    and any categories appearing in the data that are not in the keymap are
    ignored
    """
    if keymap is None:
        keymap = []
        for col in data.T:
            uniques = set(list(col))
            keymap.append(dict((key, i) for i, key in enumerate(uniques)))
    total_pts = data.shape[0]
    outdat = []
    for i, col in enumerate(data.T):
        km = keymap[i]
        num_labels = len(km)
        spmat = sparse.lil_matrix((total_pts, num_labels))
        for j, val in enumerate(col):
            if val in km:
                spmat[j, km[val]] = 1
        outdat.append(spmat)
    outdat = sparse.hstack(outdat).tocsr()
    return outdat, keymap


def _do_watch_progress(filename, sock, handler):
    """Function to run in a separate gevent greenlet to read progress
    events from a unix-domain socket."""
    connection, client_address = sock.accept()
    data = b''
    try:
        while True:
            more_data = connection.recv(16)
            if not more_data:
                break
            data += more_data
            lines = data.split(b'\n')
            for line in lines[:-1]:
                line = line.decode()
                parts = line.split('=')
                key = parts[0] if len(parts) > 0 else None
                value = parts[1] if len(parts) > 1 else None
                handler(key, value)
            data = lines[-1]
    finally:
        connection.close()


@contextlib.contextmanager
def _watch_progress(handler):
    """Context manager for creating a unix-domain socket and listen for
    ffmpeg progress events.

    The socket filename is yielded from the context manager and the
    socket is closed when the context manager is exited.

    Args:
        handler: a function to be called when progress events are
            received; receives a ``key`` argument and ``value``
            argument. (The example ``show_progress`` below uses tqdm)

    Yields:
        socket_filename: the name of the socket file.
    """
    with _tmpdir_scope() as tmpdir:
        socket_filename = os.path.join(tmpdir, 'sock')
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        with contextlib.closing(sock):
            sock.bind(socket_filename)
            sock.listen(1)
            child = gevent.spawn(_do_watch_progress, socket_filename, sock, handler)
            try:
                yield socket_filename
            except:
                gevent.kill(child)
                raise



@contextlib.contextmanager
def show_progress(total_duration):
    """Create a unix-domain socket to watch progress and render tqdm
    progress bar."""
    with tqdm(total=round(total_duration, 2)) as bar:
        def handler(key, value):
            if key == 'out_time_ms':
                time = round(float(value) / 1000000., 2)
                bar.update(time - bar.n)
            elif key == 'progress' and value == 'end':
                bar.update(bar.total - bar.n)
        with _watch_progress(handler) as socket_filename:
            yield socket_filename


def run(in_filename, out_filename, process_frame):
    width, height = get_video_size(in_filename)
    process1 = start_ffmpeg_process1(in_filename)
    process2 = start_ffmpeg_process2(out_filename, width, height)
    while True:
        in_frame = read_frame(process1, width, height)
        if in_frame is None:
            logger.info('End of input stream')
            break

        logger.debug('Processing frame')
        out_frame = process_frame(in_frame)
        write_frame(process2, out_frame)

    logger.info('Waiting for ffmpeg process1')
    process1.wait()

    logger.info('Waiting for ffmpeg process2')
    process2.stdin.close()
    process2.wait()

    logger.info('Done')


class DeepDream(object):
    '''DeepDream implementation, adapted from official tensorflow deepdream tutorial:
    https://github.com/tensorflow/tensorflow/tree/master/tensorflow/examples/tutorials/deepdream

    Credit: Alexander Mordvintsev
    '''

    _DOWNLOAD_URL = 'https://storage.googleapis.com/download.tensorflow.org/models/inception5h.zip'
    _ZIP_FILENAME = 'deepdream_model.zip'
    _MODEL_FILENAME = 'tensorflow_inception_graph.pb'

    @staticmethod
    def _download_model():
        logger.info('Downloading deepdream model...')
        try:
            from urllib.request import urlretrieve  # python 3
        except ImportError:
            from urllib import urlretrieve  # python 2
        urlretrieve(DeepDream._DOWNLOAD_URL, DeepDream._ZIP_FILENAME)

        logger.info('Extracting deepdream model...')
        zipfile.ZipFile(DeepDream._ZIP_FILENAME, 'r').extractall('.')

    @staticmethod
    def _tffunc(*argtypes):
        '''Helper that transforms TF-graph generating function into a regular one.
        See `_resize` function below.
        '''
        placeholders = list(map(tf.placeholder, argtypes))

        def wrap(f):
            out = f(*placeholders)

            def wrapper(*args, **kw):
                return out.eval(dict(zip(placeholders, args)), session=kw.get('session'))

            return wrapper

        return wrap

    @staticmethod
    def _base_resize(img, size):
        '''Helper function that uses TF to resize an image'''
        img = tf.expand_dims(img, 0)
        return tf.image.resize_bilinear(img, size)[0, :, :, :]

    def __init__(self):
        if not os.path.exists(DeepDream._MODEL_FILENAME):
            self._download_model()

        self._graph = tf.Graph()
        self._session = tf.InteractiveSession(graph=self._graph)
        self._resize = self._tffunc(np.float32, np.int32)(self._base_resize)
        with tf.gfile.FastGFile(DeepDream._MODEL_FILENAME, 'rb') as f:
            graph_def = tf.GraphDef()
            graph_def.ParseFromString(f.read())
        self._t_input = tf.placeholder(np.float32, name='input')  # define the input tensor
        imagenet_mean = 117.0
        t_preprocessed = tf.expand_dims(self._t_input - imagenet_mean, 0)
        tf.import_graph_def(graph_def, {'input': t_preprocessed})

        self.t_obj = self.T('mixed4d_3x3_bottleneck_pre_relu')[:, :, :, 139]
        # self.t_obj = tf.square(self.T('mixed4c'))

    def T(self, layer_name):
        '''Helper for getting layer output tensor'''
        return self._graph.get_tensor_by_name('import/%s:0' % layer_name)

    def _calc_grad_tiled(self, img, t_grad, tile_size=512):
        '''Compute the value of tensor t_grad over the image in a tiled way.
        Random shifts are applied to the image to blur tile boundaries over
        multiple iterations.'''
        sz = tile_size
        h, w = img.shape[:2]
        sx, sy = np.random.randint(sz, size=2)
        img_shift = np.roll(np.roll(img, sx, 1), sy, 0)
        grad = np.zeros_like(img)
        for y in range(0, max(h - sz // 2, sz), sz):
            for x in range(0, max(w - sz // 2, sz), sz):
                sub = img_shift[y:y + sz, x:x + sz]
                g = self._session.run(t_grad, {self._t_input: sub})
                grad[y:y + sz, x:x + sz] = g
        return np.roll(np.roll(grad, -sx, 1), -sy, 0)

    def process_frame(self, frame, iter_n=10, step=1.5, octave_n=4, octave_scale=1.4):
        t_score = tf.reduce_mean(self.t_obj)  # defining the optimization objective
        t_grad = tf.gradients(t_score, self._t_input)[0]  # behold the power of automatic differentiation!

        # split the image into a number of octaves
        img = frame
        octaves = []
        for i in range(octave_n - 1):
            hw = img.shape[:2]
            lo = self._resize(img, np.int32(np.float32(hw) / octave_scale))
            hi = img - self._resize(lo, hw)
            img = lo
            octaves.append(hi)

        # generate details octave by octave
        for octave in range(octave_n):
            if octave > 0:
                hi = octaves[-octave]
                img = self._resize(img, hi.shape[:2]) + hi
            for i in range(iter_n):
                g = self._calc_grad_tiled(img, t_grad)
                img += g * (step / (np.abs(g).mean() + 1e-7))
                # print('.',end = ' ')
        return img

def runFlask():
    if platform.system() == "Windows":
        app.run(host=conf.serverHost, port=conf.serverPort)
    else:
        import gunicorn.app.base

        class StandaloneApplication(gunicorn.app.base.BaseApplication):

            def __init__(self, app, options=None):
                self.options = options or {}
                self.application = app
                super(StandaloneApplication, self).__init__()

            def load_config(self):
                _config = dict([(key, value) for key, value in iteritems(self.options)
                                if key in self.cfg.settings and value is not None])
                for key, value in iteritems(_config):
                    self.cfg.set(key.lower(), value)

            def load(self):
                return self.application

        _options = {
            'bind': '%s:%s' % (conf.serverHost, conf.serverPort),
            'workers': 4,
            'accesslog': '-',  # log to stdout
            'access_log_format': '%(h)s %(l)s %(t)s "%(r)s" %(s)s "%(a)s"'
        }
        StandaloneApplication(app, _options).run()


class DbClient(withMetaclass(Singleton)):
    """
    DbClient DB工厂类 提供get/put/update/pop/delete/exists/getAll/clean/getCount/changeTable方法


    抽象方法定义：
        get(): 随机返回一个proxy;
        put(proxy): 存入一个proxy;
        pop(): 顺序返回并删除一个proxy;
        update(proxy): 更新指定proxy信息;
        delete(proxy): 删除指定proxy;
        exists(proxy): 判断指定proxy是否存在;
        getAll(): 返回所有代理;
        clean(): 清除所有proxy信息;
        getCount(): 返回proxy统计信息;
        changeTable(name): 切换操作对象


        所有方法需要相应类去具体实现：
            ssdb: ssdbClient.py
            redis: redisClient.py
            mongodb: mongodbClient.py

    """

    def __init__(self, db_conn):
        """
        init
        :return:
        """
        self.parseDbConn(db_conn)
        self.__initDbClient()

    @classmethod
    def parseDbConn(cls, db_conn):
        db_conf = urlparse(db_conn)
        cls.db_type = db_conf.scheme.upper().strip()
        cls.db_host = db_conf.hostname
        cls.db_port = db_conf.port
        cls.db_user = db_conf.username
        cls.db_pwd = db_conf.password
        cls.db_name = db_conf.path[1:]
        return cls

    def __initDbClient(self):
        """
        init DB Client
        :return:
        """
        __type = None
        if "SSDB" == self.db_type:
            __type = "ssdbClient"
        elif "REDIS" == self.db_type:
            __type = "redisClient"
        else:
            pass
        assert __type, 'type error, Not support DB type: {}'.format(self.db_type)
        self.client = getattr(__import__(__type), "%sClient" % self.db_type.title())(host=self.db_host,
                                                                                     port=self.db_port,
                                                                                     username=self.db_user,
                                                                                     password=self.db_pwd,
                                                                                     db=self.db_name)

    def get(self, https, **kwargs):
        return self.client.get(https, **kwargs)

    def put(self, key, **kwargs):
        return self.client.put(key, **kwargs)

    def update(self, key, value, **kwargs):
        return self.client.update(key, value, **kwargs)

    def delete(self, key, **kwargs):
        return self.client.delete(key, **kwargs)

    def exists(self, key, **kwargs):
        return self.client.exists(key, **kwargs)

    def pop(self, https, **kwargs):
        return self.client.pop(https, **kwargs)

    def getAll(self, https):
        return self.client.getAll(https)

    def clear(self):
        return self.client.clear()

    def changeTable(self, name):
        self.client.changeTable(name)

    def getCount(self):
        return self.client.getCount()

    def test(self):
        return self.client.test()

class RedisClient(object):
    """
    Redis client

    Redis中代理存放的结构为hash：
    key为ip:port, value为代理属性的字典;

    """

    def __init__(self, **kwargs):
        """
        init
        :param host: host
        :param port: port
        :param password: password
        :param db: db
        :return:
        """
        self.name = ""
        kwargs.pop("username")
        self.__conn = Redis(connection_pool=BlockingConnectionPool(decode_responses=True,
                                                                   timeout=5,
                                                                   socket_timeout=5,
                                                                   **kwargs))

    def get(self, https):
        """
        返回一个代理
        :return:
        """
        if https:
            items = self.__conn.hvals(self.name)
            proxies = list(filter(lambda x: json.loads(x).get("https"), items))
            return choice(proxies) if proxies else None
        else:
            proxies = self.__conn.hkeys(self.name)
            proxy = choice(proxies) if proxies else None
            return self.__conn.hget(self.name, proxy) if proxy else None

    def put(self, proxy_obj):
        """
        将代理放入hash, 使用changeTable指定hash name
        :param proxy_obj: Proxy obj
        :return:
        """
        data = self.__conn.hset(self.name, proxy_obj.proxy, proxy_obj.to_json)
        return data

    def pop(self, https):
        """
        弹出一个代理
        :return: dict {proxy: value}
        """
        proxy = self.get(https)
        if proxy:
            self.__conn.hdel(self.name, json.loads(proxy).get("proxy", ""))
        return proxy if proxy else None

    def delete(self, proxy_str):
        """
        移除指定代理, 使用changeTable指定hash name
        :param proxy_str: proxy str
        :return:
        """
        return self.__conn.hdel(self.name, proxy_str)

    def exists(self, proxy_str):
        """
        判断指定代理是否存在, 使用changeTable指定hash name
        :param proxy_str: proxy str
        :return:
        """
        return self.__conn.hexists(self.name, proxy_str)

    def update(self, proxy_obj):
        """
        更新 proxy 属性
        :param proxy_obj:
        :return:
        """
        return self.__conn.hset(self.name, proxy_obj.proxy, proxy_obj.to_json)

    def getAll(self, https):
        """
        字典形式返回所有代理, 使用changeTable指定hash name
        :return:
        """
        items = self.__conn.hvals(self.name)
        if https:
            return list(filter(lambda x: json.loads(x).get("https"), items))
        else:
            return items

    def clear(self):
        """
        清空所有代理, 使用changeTable指定hash name
        :return:
        """
        return self.__conn.delete(self.name)

    def getCount(self):
        """
        返回代理数量
        :return:
        """
        proxies = self.getAll(https=False)
        return {'total': len(proxies), 'https': len(list(filter(lambda x: json.loads(x).get("https"), proxies)))}

    def changeTable(self, name):
        """
        切换操作对象
        :param name:
        :return:
        """
        self.name = name

    def test(self):
        log = LogHandler('redis_client')
        try:
            self.getCount()
        except TimeoutError as e:
            log.error('redis connection time out: %s' % str(e), exc_info=True)
            return e
        except ConnectionError as e:
            log.error('redis connection error: %s' % str(e), exc_info=True)
            return e
        except ResponseError as e:
            log.error('redis connection error: %s' % str(e), exc_info=True)
            return e

class SsdbClient(object):
    """
    SSDB client

    SSDB中代理存放的结构为hash：
    key为代理的ip:por, value为代理属性的字典;
    """

    def __init__(self, **kwargs):
        """
        init
        :param host: host
        :param port: port
        :param password: password
        :return:
        """
        self.name = ""
        kwargs.pop("username")
        self.__conn = Redis(connection_pool=BlockingConnectionPool(decode_responses=True,
                                                                   timeout=5,
                                                                   socket_timeout=5,
                                                                   **kwargs))

    def get(self, https):
        """
        从hash中随机返回一个代理
        :return:
        """
        if https:
            items_dict = self.__conn.hgetall(self.name)
            proxies = list(filter(lambda x: json.loads(x).get("https"), items_dict.values()))
            return choice(proxies) if proxies else None
        else:
            proxies = self.__conn.hkeys(self.name)
            proxy = choice(proxies) if proxies else None
            return self.__conn.hget(self.name, proxy) if proxy else None

    def put(self, proxy_obj):
        """
        将代理放入hash
        :param proxy_obj: Proxy obj
        :return:
        """
        result = self.__conn.hset(self.name, proxy_obj.proxy, proxy_obj.to_json)
        return result

    def pop(self, https):
        """
        顺序弹出一个代理
        :return: proxy
        """
        proxy = self.get(https)
        if proxy:
            self.__conn.hdel(self.name, json.loads(proxy).get("proxy", ""))
        return proxy if proxy else None

    def delete(self, proxy_str):
        """
        移除指定代理, 使用changeTable指定hash name
        :param proxy_str: proxy str
        :return:
        """
        self.__conn.hdel(self.name, proxy_str)

    def exists(self, proxy_str):
        """
        判断指定代理是否存在, 使用changeTable指定hash name
        :param proxy_str: proxy str
        :return:
        """
        return self.__conn.hexists(self.name, proxy_str)

    def update(self, proxy_obj):
        """
        更新 proxy 属性
        :param proxy_obj:
        :return:
        """
        self.__conn.hset(self.name, proxy_obj.proxy, proxy_obj.to_json)

    def getAll(self, https):
        """
        字典形式返回所有代理, 使用changeTable指定hash name
        :return:
        """
        item_dict = self.__conn.hgetall(self.name)
        if https:
            return list(filter(lambda x: json.loads(x).get("https"), item_dict.values()))
        else:
            return item_dict.values()

    def clear(self):
        """
        清空所有代理, 使用changeTable指定hash name
        :return:
        """
        return self.__conn.delete(self.name)

    def getCount(self):
        """
        返回代理数量
        :return:
        """
        proxies = self.getAll(https=False)
        return {'total': len(proxies), 'https': len(list(filter(lambda x: json.loads(x).get("https"), proxies)))}

    def changeTable(self, name):
        """
        切换操作对象
        :param name:
        :return:
        """
        self.name = name

    def test(self):
        log = LogHandler('ssdb_client')
        try:
            self.getCount()
        except TimeoutError as e:
            log.error('ssdb connection time out: %s' % str(e), exc_info=True)
            return e
        except ConnectionError as e:
            log.error('ssdb connection error: %s' % str(e), exc_info=True)
            return e
        except ResponseError as e:
            log.error('ssdb connection error: %s' % str(e), exc_info=True)
            return e


def _tagui_output():
    """function to wait for tagui output file to read and delete it"""
    global _tagui_delay, _tagui_init_directory

    # to handle user changing current directory after init() is called
    init_directory_output_file = os.path.join(_tagui_init_directory, 'rpa_python.txt')

    # sleep to not splurge cpu cycles in while loop
    while not os.path.isfile('rpa_python.txt'):
        if os.path.isfile(init_directory_output_file): break
        time.sleep(_tagui_delay)

    # roundabout implementation to ensure backward compatibility
    if os.path.isfile('rpa_python.txt'):
        tagui_output_file = _py23_open('rpa_python.txt', 'r')
        tagui_output_text = _py23_read(tagui_output_file.read())
        tagui_output_file.close()
        os.remove('rpa_python.txt')
    else:
        tagui_output_file = _py23_open(init_directory_output_file, 'r')
        tagui_output_text = _py23_read(tagui_output_file.read())
        tagui_output_file.close()
        os.remove(init_directory_output_file)

    return tagui_output_text


def _tagui_delta(base_directory = None):
    """function to download stable delta files from tagui cutting edge version"""
    global __version__
    if base_directory is None or base_directory == '': return False
    # skip downloading if it is already done before for current release
    if os.path.isfile(base_directory + '/' + 'rpa_python_' + __version__): return True

    # define list of key tagui files to be downloaded and synced locally
    delta_list = ['tagui', 'tagui.cmd', 'end_processes', 'end_processes.cmd',
                    'tagui_header.js', 'tagui_parse.php', 'tagui.sikuli/tagui.py']

    for delta_file in delta_list:
        tagui_delta_url = 'https://raw.githubusercontent.com/tebelorg/Tump/master/TagUI-Python/' + delta_file
        tagui_delta_file = base_directory + '/' + 'src' + '/' + delta_file
        if not download(tagui_delta_url, tagui_delta_file): return False

    # make sure execute permission is there for .tagui/src/tagui and end_processes
    if platform.system() in ['Linux', 'Darwin']:
        os.system('chmod -R 755 "' + base_directory + '/' + 'src' + '/' + 'tagui" > /dev/null 2>&1')
        os.system('chmod -R 755 "' + base_directory + '/' + 'src' + '/' + 'end_processes" > /dev/null 2>&1')

    # create marker file to skip syncing delta files next time for current release
    delta_done_file = _py23_open(base_directory + '/' + 'rpa_python_' + __version__, 'w')
    delta_done_file.write(_py23_write('TagUI installation files used by RPA for Python'))
    delta_done_file.close()
    return True

def _patch_macos_pjs():
    """patch PhantomJS to latest v2.1.1 that plays well with new macOS versions"""
    if platform.system() == 'Darwin' and not os.path.isdir(tagui_location() + '/.tagui/src/phantomjs_old'):
        original_directory = os.getcwd(); os.chdir(tagui_location() + '/.tagui/src')
        print('[RPA][INFO] - downloading latest PhantomJS to fix OpenSSL issue')
        download('https://github.com/tebelorg/Tump/releases/download/v1.0.0/phantomjs-2.1.1-macosx.zip', 'phantomjs.zip')
        if not os.path.isfile('phantomjs.zip'):
            os.chdir(original_directory)
            show_error('[RPA][ERROR] - unable to download latest PhantomJS v2.1.1')
            return False
        unzip('phantomjs.zip'); os.rename('phantomjs', 'phantomjs_old'); os.rename('phantomjs-2.1.1-macosx', 'phantomjs')
        if os.path.isfile('phantomjs.zip'): os.remove('phantomjs.zip')
        os.system('chmod -R 755 phantomjs > /dev/null 2>&1')
        os.chdir(original_directory); return True
    else:
        return True

def _patch_macos_py3():
    """because newer macOS does not have python command only python3 command"""
    if platform.system() == 'Darwin' and not os.path.isfile(tagui_location() + '/.tagui/src/py3_patched'):
        if not os.system('python --version > /dev/null 2>&1') == 0:
            if os.system('python3 --version > /dev/null 2>&1') == 0:
                list_of_patch_files = [tagui_location() + '/.tagui/src/casperjs/bin/casperjs',
                                       tagui_location() + '/.tagui/src/casperjs/tests/clitests/runtests.py',
                                       tagui_location() + '/.tagui/src/slimerjs/slimerjs.py']
                for patch_file in list_of_patch_files:
                    dump(load(patch_file).replace('#!/usr/bin/env python', '#!/usr/bin/env python3'), patch_file)
                dump('python updated to python 3', tagui_location() + '/.tagui/src/py3_patched')
    return True


def unzip(file_to_unzip=None, unzip_location=None):
    """function to unzip zip file to specified location"""
    import zipfile

    if file_to_unzip is None or file_to_unzip == '':
        show_error('[RPA][ERROR] - filename missing for unzip()')
        return False
    elif not os.path.isfile(file_to_unzip):
        show_error('[RPA][ERROR] - file specified missing for unzip()')
        return False

    zip_file = zipfile.ZipFile(file_to_unzip, 'r')

    if unzip_location is None or unzip_location == '':
        zip_file.extractall()
    else:
        zip_file.extractall(unzip_location)

    zip_file.close()
    return True


def setup():
    """function to setup TagUI to user home folder on Linux / macOS / Windows"""

    # get user home folder location to setup tagui
    home_directory = tagui_location()

    print('[RPA][INFO] - setting up TagUI for use in your Python environment')

    # special check for macOS - download() will fail due to no SSL certs for Python 3
    if platform.system() == 'Darwin' and _python3_env():
        if os.system('/Applications/Python\ 3.9/Install\ Certificates.command > /dev/null 2>&1') != 0:
            if os.system('/Applications/Python\ 3.8/Install\ Certificates.command > /dev/null 2>&1') != 0:
                if os.system('/Applications/Python\ 3.7/Install\ Certificates.command > /dev/null 2>&1') != 0:
                    os.system('/Applications/Python\ 3.6/Install\ Certificates.command > /dev/null 2>&1')

    # set tagui zip filename for respective operating systems
    if platform.system() == 'Linux':
        tagui_zip_file = 'TagUI_Linux.zip'
    elif platform.system() == 'Darwin':
        tagui_zip_file = 'TagUI_macOS.zip'
    elif platform.system() == 'Windows':
        tagui_zip_file = 'TagUI_Windows.zip'
    else:
        show_error('[RPA][ERROR] - unknown ' + platform.system() + ' operating system to setup TagUI')
        return False

    if not os.path.isfile('rpa_python.zip'):
        # primary installation pathway by downloading from internet, requiring internet access
        print('[RPA][INFO] - downloading TagUI (~200MB) and unzipping to below folder...')
        print('[RPA][INFO] - ' + home_directory)

        # set tagui zip download url and download zip for respective operating systems
        tagui_zip_url = 'https://github.com/tebelorg/Tump/releases/download/v1.0.0/' + tagui_zip_file
        if not download(tagui_zip_url, home_directory + '/' + tagui_zip_file):
            # error message is shown by download(), no need for message here
            return False

        # unzip downloaded zip file to user home folder
        unzip(home_directory + '/' + tagui_zip_file, home_directory)
        if not os.path.isfile(home_directory + '/' + 'tagui' + '/' + 'src' + '/' + 'tagui'):
            show_error('[RPA][ERROR] - unable to unzip TagUI to ' + home_directory)
            return False

    else:
        # secondary installation pathway by using the rpa_python.zip generated from pack()
        print('[RPA][INFO] - unzipping TagUI (~200MB) from rpa_python.zip to below folder...')
        print('[RPA][INFO] - ' + home_directory)

        import shutil
        shutil.move('rpa_python.zip', home_directory + '/' + tagui_zip_file)

        if not os.path.isdir(home_directory + '/tagui'): os.mkdir(home_directory + '/tagui')
        unzip(home_directory + '/' + tagui_zip_file, home_directory + '/tagui')
        if not os.path.isfile(home_directory + '/' + 'tagui' + '/' + 'src' + '/' + 'tagui'):
            show_error('[RPA][ERROR] - unable to unzip TagUI to ' + home_directory)
            return False

    # set correct tagui folder for different operating systems
    if platform.system() == 'Windows':
        tagui_directory = home_directory + '/' + 'tagui'
    else:
        tagui_directory = home_directory + '/' + '.tagui'

        # overwrite tagui to .tagui folder for Linux / macOS

        # first rename existing .tagui folder to .tagui_previous
        if os.path.isdir(tagui_directory):
            os.rename(tagui_directory, tagui_directory + '_previous')

        # next rename extracted tagui folder (verified earlier) to .tagui
        os.rename(home_directory + '/' + 'tagui', tagui_directory)

        # finally remove .tagui_previous folder if it exists
        if os.path.isdir(tagui_directory + '_previous'):
            import shutil
            shutil.rmtree(tagui_directory + '_previous')

    # after unzip, remove downloaded zip file to save disk space
    if os.path.isfile(home_directory + '/' + tagui_zip_file):
        os.remove(home_directory + '/' + tagui_zip_file)

    # download stable delta files from tagui cutting edge version
    print('[RPA][INFO] - done. syncing TagUI with stable cutting edge version')
    if not _tagui_delta(tagui_directory): return False

    # perform Linux specific setup actions
    if platform.system() == 'Linux':
        # zipfile extractall does not preserve execute permissions
        # invoking chmod to set all files with execute permissions
        # and update delta tagui/src/tagui with execute permission
        if os.system('chmod -R 755 "' + tagui_directory + '" > /dev/null 2>&1') != 0:
            show_error('[RPA][ERROR] - unable to set permissions for .tagui folder')
            return False

            # check that php, a dependency for tagui, is installed and working
        if os.system('php --version > /dev/null 2>&1') != 0:
            print('[RPA][INFO] - PHP is not installed by default on your Linux distribution')
            print('[RPA][INFO] - google how to install PHP (eg for Ubuntu, apt-get install php)')
            print('[RPA][INFO] - after that, TagUI ready for use in your Python environment')
            print('[RPA][INFO] - visual automation (optional) requires special setup on Linux,')
            print('[RPA][INFO] - see the link below to install OpenCV and Tesseract libraries')
            print('[RPA][INFO] - https://sikulix-2014.readthedocs.io/en/latest/newslinux.html')
            return False

        else:
            print('[RPA][INFO] - TagUI now ready for use in your Python environment')
            print('[RPA][INFO] - visual automation (optional) requires special setup on Linux,')
            print('[RPA][INFO] - see the link below to install OpenCV and Tesseract libraries')
            print('[RPA][INFO] - https://sikulix-2014.readthedocs.io/en/latest/newslinux.html')

    # perform macOS specific setup actions
    if platform.system() == 'Darwin':
        # zipfile extractall does not preserve execute permissions
        # invoking chmod to set all files with execute permissions
        # and update delta tagui/src/tagui with execute permission
        if os.system('chmod -R 755 "' + tagui_directory + '" > /dev/null 2>&1') != 0:
            show_error('[RPA][ERROR] - unable to set permissions for .tagui folder')
            return False

        # patch PhantomJS to solve OpenSSL issue
        if not _patch_macos_pjs(): return False
        # patch files to solve no python issue
        if not _patch_macos_py3(): return False
        print('[RPA][INFO] - TagUI now ready for use in your Python environment')

    # perform Windows specific setup actions
    if platform.system() == 'Windows':
        # check that tagui packaged php is working, it has dependency on MSVCR110.dll
        if os.system('"' + tagui_directory + '/' + 'src' + '/' + 'php/php.exe" -v > nul 2>&1') != 0:
            print('[RPA][INFO] - now installing missing Visual C++ Redistributable dependency')

            # download from hosted setup file, if not already present when deployed using pack()
            if not os.path.isfile(tagui_directory + '/vcredist_x86.exe'):
                vcredist_x86_url = 'https://raw.githubusercontent.com/tebelorg/Tump/master/vcredist_x86.exe'
                if not download(vcredist_x86_url, tagui_directory + '/vcredist_x86.exe'):
                    return False

            # run setup to install the MSVCR110.dll dependency (user action required)
            os.system('"' + tagui_directory + '/vcredist_x86.exe"')

            # check again if tagui packaged php is working, after installing vcredist_x86.exe
            if os.system('"' + tagui_directory + '/' + 'src' + '/' + 'php/php.exe" -v > nul 2>&1') != 0:
                print('[RPA][INFO] - MSVCR110.dll is still missing, install vcredist_x86.exe from')
                print('[RPA][INFO] - the vcredist_x86.exe file in ' + home_directory + '\\tagui or from')
                print('[RPA][INFO] - https://www.microsoft.com/en-us/download/details.aspx?id=30679')
                print('[RPA][INFO] - after that, TagUI ready for use in your Python environment')
                return False

            else:
                print('[RPA][INFO] - TagUI now ready for use in your Python environment')

        else:
            print('[RPA][INFO] - TagUI now ready for use in your Python environment')

    return True


def init(visual_automation=False, chrome_browser=True, headless_mode=False, turbo_mode=False):
    """start and connect to tagui process by checking tagui live mode readiness"""

    global _process, _tagui_started, _tagui_id, _tagui_visual, _tagui_chrome, _tagui_init_directory, _tagui_download_directory

    if _tagui_started:
        show_error('[RPA][ERROR] - use close() before using init() again')
        return False

    # reset id to track instruction count from rpa python to tagui
    _tagui_id = 0

    # reset variable to track original directory when init() was called
    _tagui_init_directory = ''

    # get user home folder location to locate tagui executable
    if platform.system() == 'Windows':
        tagui_directory = tagui_location() + '/' + 'tagui'
    else:
        tagui_directory = tagui_location() + '/' + '.tagui'

    tagui_executable = tagui_directory + '/' + 'src' + '/' + 'tagui'
    end_processes_executable = tagui_directory + '/' + 'src' + '/' + 'end_processes'

    # if tagui executable is not found, initiate setup() to install tagui
    if not os.path.isfile(tagui_executable):
        if not setup():
            # error message is shown by setup(), no need for message here
            return False

    # sync tagui delta files for current release if needed
    if not _tagui_delta(tagui_directory): return False

    # on macOS, patch PhantomJS to latest v2.1.1 to solve OpenSSL issue
    if platform.system() == 'Darwin' and not _patch_macos_pjs(): return False
    # newer macOS has no python command, patch some files header to python3
    if platform.system() == 'Darwin' and not _patch_macos_py3(): return False

    # create entry flow to launch SikuliX accordingly
    if visual_automation:
        # check for working java jdk for visual automation mode
        if platform.system() == 'Windows':
            shell_silencer = '> nul 2>&1'
        else:
            shell_silencer = '> /dev/null 2>&1'

        # check whether java is installed on the computer
        if os.system('java -version ' + shell_silencer) != 0:
            print('[RPA][INFO] - to use visual automation mode, OpenJDK v8 (64-bit) or later is required')
            print('[RPA][INFO] - download from Amazon Corretto\'s website - https://aws.amazon.com/corretto')
            print('[RPA][INFO] - OpenJDK is preferred over Java JDK which is free for non-commercial use only')
            return False
        else:
            # then check whether it is 64-bit required by sikulix
            os.system('java -version > java_version.txt 2>&1')
            java_version_info = load('java_version.txt').lower()
            os.remove('java_version.txt')
            if '64 bit' not in java_version_info and '64-bit' not in java_version_info:
                print('[RPA][INFO] - to use visual automation mode, OpenJDK v8 (64-bit) or later is required')
                print('[RPA][INFO] - download from Amazon Corretto\'s website - https://aws.amazon.com/corretto')
                print('[RPA][INFO] - OpenJDK is preferred over Java JDK which is free for non-commercial use only')
                return False
            else:
                # start a dummy first run if never run before, to let sikulix integrate jython
                sikulix_folder = tagui_directory + '/' + 'src' + '/' + 'sikulix'
                if os.path.isfile(sikulix_folder + '/' + 'jython-standalone-2.7.1.jar'):
                    os.system('java -jar "' + sikulix_folder + '/' + 'sikulix.jar" -h ' + shell_silencer)
                _visual_flow()
    else:
        _python_flow()

    # create tagui_local.js for custom functions
    _tagui_local()

    # invoke web browser accordingly with tagui option
    browser_option = ''
    if chrome_browser:
        browser_option = 'chrome'
    if headless_mode:
        browser_option = 'headless'

    # special handling for turbo mode to run 10X faster
    tagui_chrome_php = tagui_directory + '/' + 'src' + '/' + 'tagui_chrome.php'
    tagui_header_js = tagui_directory + '/' + 'src' + '/' + 'tagui_header.js'
    tagui_sikuli_py = tagui_directory + '/' + 'src' + '/' + 'tagui.sikuli/tagui.py'
    if not turbo_mode:
        dump(load(tagui_chrome_php).replace('$scan_period = 10000;', '$scan_period = 100000;'), tagui_chrome_php)
        dump(load(tagui_header_js).replace('function sleep(ms) {ms *= 0.1; //', 'function sleep(ms) { //').replace(
            "chrome_step('Input.insertText',{text: value});};",
            "for (var character = 0, length = value.length; character < length; character++) {\nchrome_step('Input.dispatchKeyEvent',{type: 'char', text: value[character]});}};"),
             tagui_header_js)
        dump(load(tagui_sikuli_py).replace(
            'scan_period = 0.05\n\n# teleport mouse instead of moving to target\nSettings.MoveMouseDelay = 0',
            'scan_period = 0.5'), tagui_sikuli_py)
    else:
        dump(load(tagui_chrome_php).replace('$scan_period = 100000;', '$scan_period = 10000;'), tagui_chrome_php)
        dump(load(tagui_header_js).replace('function sleep(ms) { //', 'function sleep(ms) {ms *= 0.1; //').replace(
            "for (var character = 0, length = value.length; character < length; character++) {\nchrome_step('Input.dispatchKeyEvent',{type: 'char', text: value[character]});}};",
            "chrome_step('Input.insertText',{text: value});};"), tagui_header_js)
        dump(load(tagui_sikuli_py).replace('scan_period = 0.5',
                                           'scan_period = 0.05\n\n# teleport mouse instead of moving to target\nSettings.MoveMouseDelay = 0'),
             tagui_sikuli_py)

    # entry shell command to invoke tagui process
    tagui_cmd = '"' + tagui_executable + '"' + ' rpa_python ' + browser_option

    # run tagui end processes script to flush dead processes
    # for eg execution ended with ctrl+c or forget to close()
    os.system('"' + end_processes_executable + '"')

    try:
        # launch tagui using subprocess
        _process = subprocess.Popen(
            tagui_cmd, shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # loop until tagui live mode is ready or tagui process has ended
        while True:

            # failsafe exit if tagui process gets killed for whatever reason
            if _process.poll() is not None:
                print('[RPA][ERROR] - following happens when starting TagUI...')
                print('')
                print('The following command is executed to start TagUI -')
                print(tagui_cmd)
                print('')
                print('It leads to following output when starting TagUI -')
                os.system(tagui_cmd)
                print('')
                _tagui_visual = False
                _tagui_chrome = False
                _tagui_started = False
                show_error()
                return False

            # read next line of output from tagui process live mode interface
            tagui_out = _tagui_read()

            # check that tagui live mode is ready then start listening for inputs
            if 'LIVE MODE - type done to quit' in tagui_out:
                # dummy + start line to clear live mode backspace char before listening
                _tagui_write('echo "[RPA][STARTED]"\n')
                _tagui_write('echo "[RPA][' + str(_tagui_id) + '] - listening for inputs"\n')
                _tagui_visual = visual_automation
                _tagui_chrome = chrome_browser
                _tagui_started = True

                # loop until tagui live mode is ready and listening for inputs
                # also check _tagui_started to handle unexpected termination
                while _tagui_started and not _ready(): pass
                if not _tagui_started:
                    show_error('[RPA][ERROR] - TagUI process ended unexpectedly')
                    return False

                # remove generated tagui flow, js code and custom functions files
                if os.path.isfile('rpa_python'): os.remove('rpa_python')
                if os.path.isfile('rpa_python.js'): os.remove('rpa_python.js')
                if os.path.isfile('rpa_python.raw'): os.remove('rpa_python.raw')
                if os.path.isfile('tagui_local.js'): os.remove('tagui_local.js')

                # increment id and prepare for next instruction
                _tagui_id = _tagui_id + 1

                # set variable to track original directory when init() was called
                _tagui_init_directory = os.getcwd()

                # set variable to track file download directory for web browser
                _tagui_download_directory = os.getcwd()

                return True

    except Exception as e:
        _tagui_visual = False
        _tagui_chrome = False
        _tagui_started = False
        show_error('[RPA][ERROR] - ' + str(e))
        return False


def pack():
    """function to pack TagUI files for installation on an air-gapped computer without internet"""

    print('[RPA][INFO] - pack() is to deploy RPA for Python to a computer without internet')
    print('[RPA][INFO] - update() is to update an existing installation deployed from pack()')
    print('[RPA][INFO] - detecting and zipping your TagUI installation to rpa_python.zip ...')

    # first make sure TagUI files have been downloaded and synced to latest stable delta files
    global _tagui_started
    if _tagui_started:
        if not close():
            return False
    if not init(False, False):
        return False
    if not close():
        return False

    # next download jython to tagui/src/sikulix folder (after init() it can be moved away)
    if platform.system() == 'Windows':
        tagui_directory = tagui_location() + '/' + 'tagui'
        # pack in Visual C++ MSVCR110.dll dependency from PHP for offline installation
        vcredist_x86_url = 'https://raw.githubusercontent.com/tebelorg/Tump/master/vcredist_x86.exe'
        if not download(vcredist_x86_url, tagui_directory + '/vcredist_x86.exe'):
            return False
    else:
        tagui_directory = tagui_location() + '/' + '.tagui'
    sikulix_directory = tagui_directory + '/' + 'src' + '/' + 'sikulix'
    sikulix_jython_url = 'https://github.com/tebelorg/Tump/releases/download/v1.0.0/jython-standalone-2.7.1.jar'
    if not download(sikulix_jython_url, sikulix_directory + '/' + 'jython-standalone-2.7.1.jar'):
        return False

    # finally zip entire TagUI installation and save a copy of tagui.py to current folder
    import shutil
    shutil.make_archive('rpa_python', 'zip', tagui_directory)
    shutil.copyfile(os.path.dirname(__file__) + '/tagui.py', 'rpa.py')

    print('[RPA][INFO] - done. copy rpa_python.zip and rpa.py to your target computer.')
    print('[RPA][INFO] - then install and use with import rpa as r followed by r.init()')
    return True


def update():
    """function to update package and TagUI files on an air-gapped computer without internet"""

    print('[RPA][INFO] - pack() is to deploy RPA for Python to a computer without internet')
    print('[RPA][INFO] - update() is to update an existing installation deployed from pack()')
    print('[RPA][INFO] - downloading latest RPA for Python and TagUI files...')

    # first download updated files to rpa_update folder and zip them to rpa_update.zip
    if not os.path.isdir('rpa_update'): os.mkdir('rpa_update')
    if not os.path.isdir('rpa_update/tagui.sikuli'): os.mkdir('rpa_update/tagui.sikuli')

    rpa_python_url = 'https://raw.githubusercontent.com/tebelorg/RPA-Python/master/tagui.py'
    if not download(rpa_python_url, 'rpa_update' + '/' + 'rpa.py'): return False

    # get version number of latest release for the package to use in generated update.py
    rpa_python_py = load('rpa_update' + '/' + 'rpa.py')
    v_front_marker = "__version__ = '";
    v_back_marker = "'"
    rpa_python_py = rpa_python_py[rpa_python_py.find(v_front_marker) + len(v_front_marker):]
    rpa_python_py = rpa_python_py[:rpa_python_py.find(v_back_marker)]

    delta_list = ['tagui', 'tagui.cmd', 'end_processes', 'end_processes.cmd',
                  'tagui_header.js', 'tagui_parse.php', 'tagui.sikuli/tagui.py']

    for delta_file in delta_list:
        tagui_delta_url = 'https://raw.githubusercontent.com/tebelorg/Tump/master/TagUI-Python/' + delta_file
        tagui_delta_file = 'rpa_update' + '/' + delta_file
        if not download(tagui_delta_url, tagui_delta_file): return False

    import shutil
    shutil.make_archive('rpa_update', 'zip', 'rpa_update')

    # next define string variables for update.py header and footer to be used in next section
    # indentation formatting has to be removed below, else unwanted indentation added to file
    update_py_header = \
        """import rpa as r
        import platform
        import base64
        import shutil
        import os
        
        rpa_update_zip = \\
        """

    update_py_footer = \
        """
        
        # create update.zip from base64 data embedded in update.py
        update_zip_file = open('update.zip','wb')
        update_zip_file.write(base64.b64decode(rpa_update_zip))
        update_zip_file.close()
        
        # unzip update.zip to tagui folder in user home directory
        if platform.system() == 'Windows':
            base_directory = os.environ['APPDATA'] + '/tagui'
        else:
            base_directory = os.path.expanduser('~') + '/.tagui'
        
        # uncomment below to define and use custom TagUI folder
        #base_directory = 'your_full_path'
        
        r.unzip('update.zip', base_directory + '/src')
        if os.path.isfile('update.zip'): os.remove('update.zip')
        
        # make sure execute permission is there for Linux / macOS
        if platform.system() in ['Linux', 'Darwin']:
            os.system('chmod -R 755 "' + base_directory + '/src/tagui" > /dev/null 2>&1')
            os.system('chmod -R 755 "' + base_directory + '/src/end_processes" > /dev/null 2>&1')
        
        # create marker file to skip syncing for current release
        delta_done_file = r._py23_open(base_directory + '/' + 'rpa_python_' + __version__, 'w')
        delta_done_file.write(r._py23_write('TagUI installation files used by RPA for Python'))
        delta_done_file.close()
        
        # move updated package file rpa.py to package folder
        shutil.move(base_directory + '/src/rpa.py', os.path.dirname(r.__file__) + '/rpa.py')
        print('[RPA][INFO] - done. RPA for Python updated to version ' + __version__)
        """

    # finally create update.py containing python code and zipped data of update in base64
    try:
        import base64
        dump("__version__ = '" + rpa_python_py + "'\n\n", 'update.py')
        write(update_py_header, 'update.py')
        update_zip_file = open('rpa_update.zip', 'rb')
        zip_base64_data = (base64.b64encode(update_zip_file.read())).decode('utf-8')
        update_zip_file.close()
        write('"""' + zip_base64_data + '"""', 'update.py')
        write(update_py_footer, 'update.py')

        # remove temporary folder and downloaded files, show result and usage message
        if os.path.isdir('rpa_update'): shutil.rmtree('rpa_update')
        if os.path.isfile('rpa_update.zip'): os.remove('rpa_update.zip')
        print('[RPA][INFO] - done. copy or email update.py to your target computer and run')
        print('[RPA][INFO] - python update.py to update RPA for Python to version ' + rpa_python_py)
        print('[RPA][INFO] - to use custom TagUI folder, set base_directory in update.py')
        return True

    except Exception as e:
        show_error('[RPA][ERROR] - ' + str(e))
        return False


def _ready():
    """internal function to check if tagui is ready to receive instructions after init() is called"""

    global _process, _tagui_started, _tagui_id, _tagui_visual, _tagui_chrome

    if not _tagui_started:
        # print output error in calling parent function instead
        return False

    try:
        # failsafe exit if tagui process gets killed for whatever reason
        if _process.poll() is not None:
            # print output error in calling parent function instead
            _tagui_visual = False
            _tagui_chrome = False
            _tagui_started = False
            return False

        # read next line of output from tagui process live mode interface
        tagui_out = _tagui_read()

        # print to screen debug output that is saved to rpa_python.log
        if debug():
            sys.stdout.write(tagui_out);
            sys.stdout.flush()

        # check if tagui live mode is listening for inputs and return result
        if tagui_out.strip().startswith('[RPA][') and tagui_out.strip().endswith('] - listening for inputs'):
            return True
        else:
            return False

    except Exception as e:
        show_error('[RPA][ERROR] - ' + str(e))
        return False


def send(tagui_instruction=None):
    """send next live mode instruction to tagui for processing if tagui is ready"""

    global _process, _tagui_started, _tagui_id, _tagui_visual, _tagui_chrome

    if not _tagui_started:
        show_error('[RPA][ERROR] - use init() before using send()')
        return False

    if tagui_instruction is None or tagui_instruction == '': return True

    try:
        # failsafe exit if tagui process gets killed for whatever reason
        if _process.poll() is not None:
            _tagui_visual = False
            _tagui_chrome = False
            _tagui_started = False
            show_error('[RPA][ERROR] - no active TagUI process to send()')
            return False

        # escape special characters for them to reach tagui correctly
        tagui_instruction = tagui_instruction.replace('\\', '\\\\')
        tagui_instruction = tagui_instruction.replace('\n', '\\n')
        tagui_instruction = tagui_instruction.replace('\r', '\\r')
        tagui_instruction = tagui_instruction.replace('\t', '\\t')
        tagui_instruction = tagui_instruction.replace('\a', '\\a')
        tagui_instruction = tagui_instruction.replace('\b', '\\b')
        tagui_instruction = tagui_instruction.replace('\f', '\\f')

        # special handling for single quote to work with _esq() for tagui
        tagui_instruction = tagui_instruction.replace('[BACKSLASH_QUOTE]', '\\\'')

        # escape backslash to display source string correctly after echoing
        echo_safe_instruction = tagui_instruction.replace('\\', '\\\\')

        # escape double quote because echo step below uses double quotes
        echo_safe_instruction = echo_safe_instruction.replace('"', '\\"')

        # echo live mode instruction, after preparing string to be echo-safe
        _tagui_write('echo "[RPA][' + str(_tagui_id) + '] - ' + echo_safe_instruction + '"\n')

        # send live mode instruction to be executed
        _tagui_write(tagui_instruction + '\n')

        # echo marker text to prepare for next instruction
        _tagui_write('echo "[RPA][' + str(_tagui_id) + '] - listening for inputs"\n')

        # loop until tagui live mode is ready and listening for inputs
        # also check _tagui_started to handle unexpected termination
        while _tagui_started and not _ready(): pass
        if not _tagui_started:
            show_error('[RPA][ERROR] - TagUI process ended unexpectedly')
            return False

        # increment id and prepare for next instruction
        _tagui_id = _tagui_id + 1

        return True

    except Exception as e:
        show_error('[RPA][ERROR] - ' + str(e))
        return False


def close():
    """disconnect from tagui process by sending 'done' trigger instruction"""

    global _process, _tagui_started, _tagui_id, _tagui_visual, _tagui_chrome, _tagui_init_directory

    if not _tagui_started:
        show_error('[RPA][ERROR] - use init() before using close()')
        return False

    try:
        # failsafe exit if tagui process gets killed for whatever reason
        if _process.poll() is not None:
            _tagui_visual = False
            _tagui_chrome = False
            _tagui_started = False
            show_error('[RPA][ERROR] - no active TagUI process to close()')
            return False

        # send 'done' instruction to terminate live mode and exit tagui
        _tagui_write('echo "[RPA][FINISHED]"\n')
        _tagui_write('done\n')

        # loop until tagui process has closed before returning control
        while _process.poll() is None: pass

        # remove again generated tagui flow, js code and custom functions files
        if os.path.isfile('rpa_python'): os.remove('rpa_python')
        if os.path.isfile('rpa_python.js'): os.remove('rpa_python.js')
        if os.path.isfile('rpa_python.raw'): os.remove('rpa_python.raw')
        if os.path.isfile('tagui_local.js'): os.remove('tagui_local.js')

        # to handle user changing current directory after init() is called
        if os.path.isfile(os.path.join(_tagui_init_directory, 'rpa_python')):
            os.remove(os.path.join(_tagui_init_directory, 'rpa_python'))
        if os.path.isfile(os.path.join(_tagui_init_directory, 'rpa_python.js')):
            os.remove(os.path.join(_tagui_init_directory, 'rpa_python.js'))
        if os.path.isfile(os.path.join(_tagui_init_directory, 'rpa_python.raw')):
            os.remove(os.path.join(_tagui_init_directory, 'rpa_python.raw'))
        if os.path.isfile(os.path.join(_tagui_init_directory, 'tagui_local.js')):
            os.remove(os.path.join(_tagui_init_directory, 'tagui_local.js'))

            # remove generated tagui log and data files if not in debug mode
        if not debug():
            if os.path.isfile('rpa_python.log'): os.remove('rpa_python.log')
            if os.path.isfile('rpa_python.txt'): os.remove('rpa_python.txt')

            # to handle user changing current directory after init() is called
            if os.path.isfile(os.path.join(_tagui_init_directory, 'rpa_python.log')):
                os.remove(os.path.join(_tagui_init_directory, 'rpa_python.log'))
            if os.path.isfile(os.path.join(_tagui_init_directory, 'rpa_python.txt')):
                os.remove(os.path.join(_tagui_init_directory, 'rpa_python.txt'))

        _tagui_visual = False
        _tagui_chrome = False
        _tagui_started = False
        return True

    except Exception as e:
        _tagui_visual = False
        _tagui_chrome = False
        _tagui_started = False
        show_error('[RPA][ERROR] - ' + str(e))
        return False


def exist(element_identifier=None):
    if not _started():
        show_error('[RPA][ERROR] - use init() before using exist()')
        return False

    if element_identifier is None or element_identifier == '':
        return False

    # return True for keywords as the computer screen always exists
    if element_identifier.lower() in ['page.png', 'page.bmp']:
        if _visual():
            return True
        else:
            show_error('[RPA][ERROR] - page.png / page.bmp requires init(visual_automation = True)')
            return False

    # pre-emptive checks if image files are specified for visual automation
    if element_identifier.lower().endswith('.png') or element_identifier.lower().endswith('.bmp'):
        if not _visual():
            show_error('[RPA][ERROR] - ' + element_identifier + ' identifier requires init(visual_automation = True)')
            return False

    # assume that (x,y) coordinates for visual automation always exist
    if element_identifier.startswith('(') and element_identifier.endswith(')'):
        if len(element_identifier.split(',')) in [2, 3]:
            if not any(c.isalpha() for c in element_identifier):
                if _visual():
                    return True
                else:
                    show_error('[RPA][ERROR] - x, y coordinates require init(visual_automation = True)')
                    return False

    send('exist_result = exist(\'' + _sdq(element_identifier) + '\').toString()')
    send('dump exist_result to rpa_python.txt')
    if _tagui_output() == 'true':
        return True
    else:
        return False


def url(webpage_url=None):
    if not _started():
        show_error('[RPA][ERROR] - use init() before using url()')
        return False

    if not _chrome():
        show_error('[RPA][ERROR] - url() requires init(chrome_browser = True)')
        return False

    if webpage_url is not None and webpage_url != '':
        if webpage_url.lower().startswith('www.'): webpage_url = 'https://' + webpage_url
        if webpage_url.startswith('http://') or webpage_url.startswith('https://'):
            if not send(_esq(webpage_url)):
                return False
            else:
                return True
        else:
            show_error('[RPA][ERROR] - URL does not begin with http:// or https:// ')
            return False

    else:
        send('dump url() to rpa_python.txt')
        url_result = _tagui_output()
        return url_result


def click(element_identifier=None, test_coordinate=None):
    if not _started():
        show_error('[RPA][ERROR] - use init() before using click()')
        return False

    if element_identifier is None or element_identifier == '':
        show_error('[RPA][ERROR] - target missing for click()')
        return False

    if test_coordinate is not None and isinstance(test_coordinate, int):
        element_identifier = coord(element_identifier, test_coordinate)

    if not exist(element_identifier):
        show_error('[RPA][ERROR] - cannot find ' + element_identifier)
        return False

    elif not send('click ' + _sdq(element_identifier)):
        return False

    else:
        return True


def rclick(element_identifier=None, test_coordinate=None):
    if not _started():
        show_error('[RPA][ERROR] - use init() before using rclick()')
        return False

    if element_identifier is None or element_identifier == '':
        show_error('[RPA][ERROR] - target missing for rclick()')
        return False

    if test_coordinate is not None and isinstance(test_coordinate, int):
        element_identifier = coord(element_identifier, test_coordinate)

    if not exist(element_identifier):
        show_error('[RPA][ERROR] - cannot find ' + element_identifier)
        return False

    elif not send('rclick ' + _sdq(element_identifier)):
        return False

    else:
        return True


def dclick(element_identifier=None, test_coordinate=None):
    if not _started():
        show_error('[RPA][ERROR] - use init() before using dclick()')
        return False

    if element_identifier is None or element_identifier == '':
        show_error('[RPA][ERROR] - target missing for dclick()')
        return False

    if test_coordinate is not None and isinstance(test_coordinate, int):
        element_identifier = coord(element_identifier, test_coordinate)

    if not exist(element_identifier):
        show_error('[RPA][ERROR] - cannot find ' + element_identifier)
        return False

    elif not send('dclick ' + _sdq(element_identifier)):
        return False

    else:
        return True


def hover(element_identifier=None, test_coordinate=None):
    if not _started():
        show_error('[RPA][ERROR] - use init() before using hover()')
        return False

    if element_identifier is None or element_identifier == '':
        show_error('[RPA][ERROR] - target missing for hover()')
        return False

    if test_coordinate is not None and isinstance(test_coordinate, int):
        element_identifier = coord(element_identifier, test_coordinate)

    if not exist(element_identifier):
        show_error('[RPA][ERROR] - cannot find ' + element_identifier)
        return False

    elif not send('hover ' + _sdq(element_identifier)):
        return False

    else:
        return True


def type(element_identifier=None, text_to_type=None, test_coordinate=None):
    if not _started():
        show_error('[RPA][ERROR] - use init() before using type()')
        return False

    if element_identifier is None or element_identifier == '':
        show_error('[RPA][ERROR] - target missing for type()')
        return False

    if text_to_type is None or text_to_type == '':
        show_error('[RPA][ERROR] - text missing for type()')
        return False

    if test_coordinate is not None and isinstance(text_to_type, int):
        element_identifier = coord(element_identifier, text_to_type)
        text_to_type = test_coordinate

    if not exist(element_identifier):
        show_error('[RPA][ERROR] - cannot find ' + element_identifier)
        return False

    elif not send('type ' + _sdq(element_identifier) + ' as ' + _esq(text_to_type)):
        return False

    else:
        return True


def select(element_identifier=None, option_value=None, test_coordinate1=None, test_coordinate2=None):
    if not _started():
        show_error('[RPA][ERROR] - use init() before using select()')
        return False

    if element_identifier is None or element_identifier == '':
        show_error('[RPA][ERROR] - target missing for select()')
        return False

    if option_value is None or option_value == '':
        show_error('[RPA][ERROR] - option value missing for select()')
        return False

    if element_identifier.lower() in ['page.png', 'page.bmp'] or option_value.lower() in ['page.png', 'page.bmp']:
        show_error('[RPA][ERROR] - page.png / page.bmp identifiers invalid for select()')
        return False

    if test_coordinate1 is not None and test_coordinate2 is not None and \
            isinstance(option_value, int) and isinstance(test_coordinate2, int):
        element_identifier = coord(element_identifier, option_value)
        option_value = coord(test_coordinate1, test_coordinate2)

        # pre-emptive checks if image files are specified for visual automation
    if element_identifier.lower().endswith('.png') or element_identifier.lower().endswith('.bmp'):
        if not _visual():
            show_error('[RPA][ERROR] - ' + element_identifier + ' identifier requires init(visual_automation = True)')
            return False

    if option_value.lower().endswith('.png') or option_value.lower().endswith('.bmp'):
        if not _visual():
            show_error('[RPA][ERROR] - ' + option_value + ' identifier requires init(visual_automation = True)')
            return False

    if not exist(element_identifier):
        show_error('[RPA][ERROR] - cannot find ' + element_identifier)
        return False

    elif not send('select ' + _sdq(element_identifier) + ' as ' + _esq(option_value)):
        return False

    else:
        return True


def read(element_identifier=None, test_coordinate1=None, test_coordinate2=None, test_coordinate3=None):
    if not _started():
        show_error('[RPA][ERROR] - use init() before using read()')
        return ''

    if element_identifier is None or element_identifier == '':
        show_error('[RPA][ERROR] - target missing for read()')
        return ''

    if test_coordinate1 is not None and isinstance(test_coordinate1, int):
        if test_coordinate2 is not None and isinstance(test_coordinate2, int):
            if test_coordinate3 is not None and isinstance(test_coordinate3, int):
                element_identifier = coord(element_identifier, test_coordinate1) + '-'
                element_identifier = element_identifier + coord(test_coordinate2, test_coordinate3)

    if element_identifier.lower() != 'page' and not exist(element_identifier):
        show_error('[RPA][ERROR] - cannot find ' + element_identifier)
        return ''

    else:
        send('read ' + _sdq(element_identifier) + ' to read_result')
        send('dump read_result to rpa_python.txt')
        read_result = _tagui_output()
        return read_result


def snap(element_identifier=None, filename_to_save=None, test_coord1=None, test_coord2=None, test_coord3=None):
    if not _started():
        show_error('[RPA][ERROR] - use init() before using snap()')
        return False

    if element_identifier is None or element_identifier == '':
        show_error('[RPA][ERROR] - target missing for snap()')
        return False

    if filename_to_save is None or filename_to_save == '':
        show_error('[RPA][ERROR] - filename missing for snap()')
        return False

    if test_coord2 is not None and test_coord3 is None:
        show_error('[RPA][ERROR] - filename missing for snap()')
        return False

    if isinstance(element_identifier, int) and isinstance(filename_to_save, int):
        if test_coord1 is not None and isinstance(test_coord1, int):
            if test_coord2 is not None and isinstance(test_coord2, int):
                if test_coord3 is not None and test_coord3 != '':
                    element_identifier = coord(element_identifier, filename_to_save) + '-'
                    element_identifier = element_identifier + coord(test_coord1, test_coord2)
                    filename_to_save = test_coord3

    if element_identifier.lower() != 'page' and not exist(element_identifier):
        show_error('[RPA][ERROR] - cannot find ' + element_identifier)
        return False

    elif not send('snap ' + _sdq(element_identifier) + ' to ' + _esq(filename_to_save)):
        return False

    else:
        return True


def load(filename_to_load=None):
    if filename_to_load is None or filename_to_load == '':
        show_error('[RPA][ERROR] - filename missing for load()')
        return ''

    elif not os.path.isfile(filename_to_load):
        show_error('[RPA][ERROR] - cannot load file ' + filename_to_load)
        return ''

    else:
        load_input_file = _py23_open(filename_to_load, 'r')
        load_input_file_text = _py23_read(load_input_file.read())
        load_input_file.close()
        return load_input_file_text


def echo(text_to_echo=''):
    print(text_to_echo)
    return True


def dump(text_to_dump=None, filename_to_save=None):
    if text_to_dump is None:
        show_error('[RPA][ERROR] - text missing for dump()')
        return False

    elif filename_to_save is None or filename_to_save == '':
        show_error('[RPA][ERROR] - filename missing for dump()')
        return False

    else:
        dump_output_file = _py23_open(filename_to_save, 'w')
        dump_output_file.write(_py23_write(text_to_dump))
        dump_output_file.close()
        return True


def write(text_to_write=None, filename_to_save=None):
    if text_to_write is None:
        show_error('[RPA][ERROR] - text missing for write()')
        return False

    elif filename_to_save is None or filename_to_save == '':
        show_error('[RPA][ERROR] - filename missing for write()')
        return False

    else:
        write_output_file = _py23_open(filename_to_save, 'a')
        write_output_file.write(_py23_write(text_to_write))
        write_output_file.close()
        return True


def ask(text_to_prompt=''):
    if _chrome():
        return dom("return prompt('" + _esq(text_to_prompt) + "')")

    else:
        if text_to_prompt == '':
            space_padding = ''
        else:
            space_padding = ' '

        if _python2_env():
            return raw_input(text_to_prompt + space_padding)
        else:
            return input(text_to_prompt + space_padding)


def telegram(telegram_id=None, text_to_send=None, custom_endpoint=None):
    if telegram_id is None or telegram_id == '':
        show_error('[RPA][ERROR] - Telegram ID missing for telegram()')
        return False

    if text_to_send is None or text_to_send == '':
        show_error('[RPA][ERROR] - text message missing for telegram()')
        return False

    # in case number is given instead of string
    telegram_id = str(telegram_id)

    telegram_endpoint = 'https://tebel.org/rpapybot'
    telegram_params = {'chat_id': telegram_id, 'text': text_to_send}

    if custom_endpoint is not None and custom_endpoint != '':
        telegram_endpoint = custom_endpoint

    # handle case where no internet or url is invalid
    try:
        if _python2_env():
            import json;
            import urllib
            telegram_endpoint = telegram_endpoint + '/sendMessage.php?' + urllib.urlencode(telegram_params)
            telegram_response = urllib.urlopen(telegram_endpoint).read()
            return json.loads(telegram_response)['ok']

        else:
            import json;
            import urllib.request;
            import urllib.parse
            telegram_endpoint = telegram_endpoint + '/sendMessage.php?' + urllib.parse.urlencode(telegram_params)
            telegram_response = urllib.request.urlopen(telegram_endpoint).read()
            return json.loads(telegram_response)['ok']

    except Exception as e:
        return False


def keyboard(keys_and_modifiers=None):
    if not _started():
        show_error('[RPA][ERROR] - use init() before using keyboard()')
        return False

    if keys_and_modifiers is None or keys_and_modifiers == '':
        show_error('[RPA][ERROR] - keys to type missing for keyboard()')
        return False

    if not _visual():
        show_error('[RPA][ERROR] - keyboard() requires init(visual_automation = True)')
        return False

    elif not send('keyboard ' + _esq(keys_and_modifiers)):
        return False

    else:
        return True


def mouse(mouse_action=None):
    if not _started():
        show_error('[RPA][ERROR] - use init() before using mouse()')
        return False

    if mouse_action is None or mouse_action == '':
        show_error('[RPA][ERROR] - \'down\' / \'up\' missing for mouse()')
        return False

    if not _visual():
        show_error('[RPA][ERROR] - mouse() requires init(visual_automation = True)')
        return False

    elif mouse_action.lower() != 'down' and mouse_action.lower() != 'up':
        show_error('[RPA][ERROR] - \'down\' / \'up\' missing for mouse()')
        return False

    elif not send('mouse ' + mouse_action):
        return False

    else:
        return True


def focus(app_to_focus=None):
    if app_to_focus is None or app_to_focus == '':
        show_error('[RPA][ERROR] - app to focus missing for focus()')
        return False

    else:
        if platform.system() == 'Windows':
            # download sendKeys.bat if not present
            if not os.path.isfile('sendKeys.bat'):
                sendKeys_url = 'https://github.com/tebelorg/Tump/releases/download/v1.0.0/sendKeys.bat'
                if not download(sendKeys_url, 'sendKeys.bat'):
                    show_error('[RPA][ERROR] - cannot download sendKeys.bat for focus()')
                    return False
            if os.system('sendKeys.bat "' + app_to_focus + '" "" > nul 2>&1') == 0:
                return True
            else:
                show_error('[RPA][ERROR] - ' + app_to_focus + ' not found for focus()')
                return False

        elif platform.system() == 'Darwin':
            if os.system('osascript -e \'tell application "' + app_to_focus + '" to activate\' > /dev/null 2>&1') == 0:
                return True
            else:
                show_error('[RPA][ERROR] - ' + app_to_focus + ' not found for focus()')
                return False

        else:
            show_error('[RPA][ERROR] - Linux not supported for focus()')
            return False


def table(element_identifier=None, filename_to_save=None):
    if not _started():
        show_error('[RPA][ERROR] - use init() before using table()')
        return False

    if element_identifier is None or element_identifier == '':
        show_error('[RPA][ERROR] - target missing for table()')
        return False

    elif filename_to_save is None or filename_to_save == '':
        show_error('[RPA][ERROR] - filename missing for table()')
        return False

    element_identifier = str(element_identifier)

    if not exist(element_identifier):
        show_error('[RPA][ERROR] - cannot find ' + element_identifier)
        return False

    elif not send('table ' + _sdq(element_identifier) + ' to ' + _esq(filename_to_save)):
        return False

    else:
        return True


def wait(delay_in_seconds=5.0):
    time.sleep(float(delay_in_seconds));
    return True


def check(condition_to_check=None, text_if_true='', text_if_false=''):
    if condition_to_check is None:
        show_error('[RPA][ERROR] - condition missing for check()')
        return False

    if condition_to_check:
        print(text_if_true)

    else:
        print(text_if_false)

    return True


def bin(file_to_bin=None, password=None, server='https://tebel.org/bin/'):
    if not _started():
        show_error('[RPA][ERROR] - use init() before using bin()')
        return ''

    if file_to_bin is None or file_to_bin == '':
        show_error('[RPA][ERROR] - file_to_bin required for bin()')
        return ''

    else:
        file_to_bin = os.path.abspath(file_to_bin)
        if not os.path.isfile(file_to_bin):
            show_error('[RPA][ERROR] - cannot find ' + file_to_bin)
            return ''

        original_url = url();
        url(server)
        if not exist('//*[@id = "message"]'):
            show_error('[RPA][ERROR] - cannot connect to ' + server)
            return ''

        file_head, file_tail = os.path.split(file_to_bin)
        type('//*[@id = "message"]', file_tail)
        if password is not None:
            type('//*[@id = "passwordinput"]', password)
        click('//*[@id = "attach"]')
        upload('#file', file_to_bin)
        click('//*[@id = "sendbutton"]')

        bin_url = read('//*[@id = "pastelink"]/a/@href')
        if bin_url == '':
            show_error('[RPA][ERROR] - failed uploading to ' + server)
        if original_url != 'about:blank':
            url(original_url)
        return bin_url


def upload(element_identifier=None, filename_to_upload=None):
    if not _started():
        show_error('[RPA][ERROR] - use init() before using upload()')
        return False

    if element_identifier is None or element_identifier == '':
        show_error('[RPA][ERROR] - target missing for upload()')
        return False

    elif filename_to_upload is None or filename_to_upload == '':
        show_error('[RPA][ERROR] - filename missing for upload()')
        return False

    elif not exist(element_identifier):
        show_error('[RPA][ERROR] - cannot find ' + element_identifier)
        return False

    elif not send('upload ' + _sdq(element_identifier) + ' as ' + _esq(filename_to_upload)):
        return False

    else:
        return True


def download(download_url=None, filename_to_save=None):
    """function for python 2/3 compatible file download from url"""

    if download_url is None or download_url == '':
        show_error('[RPA][ERROR] - download URL missing for download()')
        return False

    # if not given, use last part of url as filename to save
    if filename_to_save is None or filename_to_save == '':
        download_url_tokens = download_url.split('/')
        filename_to_save = download_url_tokens[-1]

    # delete existing file if exist to ensure freshness
    if os.path.isfile(filename_to_save):
        os.remove(filename_to_save)

    # handle case where url is invalid or has no content
    try:
        if _python2_env():
            import urllib;
            urllib.urlretrieve(download_url, filename_to_save)
        else:
            import urllib.request;
            urllib.request.urlretrieve(download_url, filename_to_save)

    except Exception as e:
        print(str(e))
        show_error('[RPA][ERROR] - failed downloading from ' + download_url + '...')
        return False

    # take the existence of downloaded file as success
    if os.path.isfile(filename_to_save):
        return True

    else:
        show_error('[RPA][ERROR] - failed downloading to ' + filename_to_save)
        return False


def frame(main_frame=None, sub_frame=None):
    if not _started():
        show_error('[RPA][ERROR] - use init() before using frame()')
        return False

    if not _chrome():
        show_error('[RPA][ERROR] - frame() requires init(chrome_browser = True)')
        return False

    # reset webpage context to document root, by sending custom tagui javascript code
    send('js chrome_step("Runtime.evaluate", {expression: "mainframe_context = null"})')
    send('js chrome_step("Runtime.evaluate", {expression: "subframe_context = null"})')
    send('js chrome_context = "document"; frame_step_offset_x = 0; frame_step_offset_y = 0;')

    # return True if no parameter, after resetting webpage context above
    if main_frame is None or main_frame == '':
        return True

    # set webpage context to main frame specified, by sending custom tagui javascript code
    frame_identifier = '(//frame|//iframe)[@name="' + main_frame + '" or @id="' + main_frame + '"]'
    if not exist(frame_identifier):
        show_error('[RPA][ERROR] - cannot find frame with @name or @id as \'' + main_frame + '\'')
        return False

    send('js new_context = "mainframe_context"')
    send('js frame_xpath = \'(//frame|//iframe)[@name="' + main_frame + '" or @id="' + main_frame + '"]\'')
    send('js frame_rect = chrome.getRect(xps666(frame_xpath))')
    send('js frame_step_offset_x = frame_rect.left; frame_step_offset_y = frame_rect.top;')
    send(
        'js chrome_step("Runtime.evaluate", {expression: new_context + " = document.evaluate(\'" + frame_xpath + "\'," + chrome_context + ",null,XPathResult.ORDERED_NODE_SNAPSHOT_TYPE,null).snapshotItem(0).contentDocument"})')
    send('js chrome_context = new_context')

    # set webpage context to sub frame if specified, by sending custom tagui javascript code
    if sub_frame is not None and sub_frame != '':
        frame_identifier = '(//frame|//iframe)[@name="' + sub_frame + '" or @id="' + sub_frame + '"]'
        if not exist(frame_identifier):
            show_error('[RPA][ERROR] - cannot find sub frame with @name or @id as \'' + sub_frame + '\'')
            return False

        send('js new_context = "subframe_context"')
        send('js frame_xpath = \'(//frame|//iframe)[@name="' + sub_frame + '" or @id="' + sub_frame + '"]\'')
        send('js frame_rect = chrome.getRect(xps666(frame_xpath))')
        send('js frame_step_offset_x = frame_rect.left; frame_step_offset_y = frame_rect.top;')
        send(
            'js chrome_step("Runtime.evaluate", {expression: new_context + " = document.evaluate(\'" + frame_xpath + "\'," + chrome_context + ",null,XPathResult.ORDERED_NODE_SNAPSHOT_TYPE,null).snapshotItem(0).contentDocument"})')
        send('js chrome_context = new_context')

    return True


def popup(string_in_url=None):
    if not _started():
        show_error('[RPA][ERROR] - use init() before using popup()')
        return False

    if not _chrome():
        show_error('[RPA][ERROR] - popup() requires init(chrome_browser = True)')
        return False

    # reset webpage context to main page, by sending custom tagui javascript code
    send(
        'js if (chrome_targetid !== "") {found_targetid = chrome_targetid; chrome_targetid = ""; chrome_step("Target.detachFromTarget", {sessionId: found_targetid});}')

    # return True if no parameter, after resetting webpage context above
    if string_in_url is None or string_in_url == '':
        return True

    # set webpage context to the popup tab specified, by sending custom tagui javascript code
    send('js found_targetid = ""; chrome_targets = []; ws_message = chrome_step("Target.getTargets", {});')
    send(
        'js try {ws_json = JSON.parse(ws_message); if (ws_json.result.targetInfos) chrome_targets = ws_json.result.targetInfos; else chrome_targets = [];} catch (e) {chrome_targets = [];}')
    send(
        'js chrome_targets.forEach(function(target) {if (target.url.indexOf("' + string_in_url + '") !== -1) found_targetid = target.targetId;})')
    send(
        'js if (found_targetid !== "") {ws_message = chrome_step("Target.attachToTarget", {targetId: found_targetid}); try {ws_json = JSON.parse(ws_message); if (ws_json.result.sessionId !== "") found_targetid = ws_json.result.sessionId; else found_targetid = "";} catch (e) {found_targetid = "";}}')
    send('js chrome_targetid = found_targetid')

    # check if chrome_targetid is successfully set to sessionid of popup tab
    send('dump chrome_targetid to rpa_python.txt')
    popup_result = _tagui_output()
    if popup_result != '':
        return True
    else:
        show_error('[RPA][ERROR] - cannot find popup tab containing URL string \'' + string_in_url + '\'')
        return False


def api(url_to_query=None):
    print('[RPA][INFO] - although TagUI supports calling APIs with headers and body,')
    print('[RPA][INFO] - recommend using requests package with lots of online docs')
    return True


def run(command_to_run=None):
    if command_to_run is None or command_to_run == '':
        show_error('[RPA][ERROR] - command(s) missing for run()')
        return ''

    else:
        if platform.system() == 'Windows':
            command_delimiter = ' & '
        else:
            command_delimiter = '; '
        return _py23_decode(subprocess.check_output(
            command_to_run + command_delimiter + 'exit 0',
            stderr=subprocess.STDOUT,
            shell=True))


def dom(statement_to_run=None):
    if not _started():
        show_error('[RPA][ERROR] - use init() before using dom()')
        return ''

    if statement_to_run is None or statement_to_run == '':
        show_error('[RPA][ERROR] - statement(s) missing for dom()')
        return ''

    if not _chrome():
        show_error('[RPA][ERROR] - dom() requires init(chrome_browser = True)')
        return ''

    else:
        send('dom ' + statement_to_run)
        send('dump dom_result to rpa_python.txt')
        dom_result = _tagui_output()
        return dom_result


def vision(command_to_run=None):
    if not _started():
        show_error('[RPA][ERROR] - use init() before using vision()')
        return False

    if command_to_run is None or command_to_run == '':
        show_error('[RPA][ERROR] - command(s) missing for vision()')
        return False

    if not _visual():
        show_error('[RPA][ERROR] - vision() requires init(visual_automation = True)')
        return False

    elif not send('vision ' + command_to_run):
        return False

    else:
        return True


def timeout(timeout_in_seconds=None):
    if not _started():
        show_error('[RPA][ERROR] - use init() before using timeout()')
        return False

    global _tagui_timeout

    if timeout_in_seconds is None:
        return float(_tagui_timeout)

    else:
        _tagui_timeout = float(timeout_in_seconds)

    if not send('timeout ' + str(timeout_in_seconds)):
        return False

    else:
        return True


def present(element_identifier=None):
    if not _started():
        show_error('[RPA][ERROR] - use init() before using present()')
        return False

    if element_identifier is None or element_identifier == '':
        return False

    # return True for keywords as the computer screen is always present
    if element_identifier.lower() in ['page.png', 'page.bmp']:
        if _visual():
            return True
        else:
            show_error('[RPA][ERROR] - page.png / page.bmp requires init(visual_automation = True)')
            return False

    # pre-emptive checks if image files are specified for visual automation
    if element_identifier.lower().endswith('.png') or element_identifier.lower().endswith('.bmp'):
        if not _visual():
            show_error('[RPA][ERROR] - ' + element_identifier + ' identifier requires init(visual_automation = True)')
            return False

    # assume that (x,y) coordinates for visual automation always exist
    if element_identifier.startswith('(') and element_identifier.endswith(')'):
        if len(element_identifier.split(',')) in [2, 3]:
            if not any(c.isalpha() for c in element_identifier):
                if _visual():
                    return True
                else:
                    show_error('[RPA][ERROR] - x, y coordinates require init(visual_automation = True)')
                    return False

    send('present_result = present(\'' + _sdq(element_identifier) + '\').toString()')
    send('dump present_result to rpa_python.txt')
    if _tagui_output() == 'true':
        return True
    else:
        return False


def count(element_identifier=None):
    if not _started():
        show_error('[RPA][ERROR] - use init() before using count()')
        return int(0)

    if element_identifier is None or element_identifier == '':
        return int(0)

    if not _chrome():
        show_error('[RPA][ERROR] - count() requires init(chrome_browser = True)')
        return int(0)

    send('count_result = count(\'' + _sdq(element_identifier) + '\').toString()')
    send('dump count_result to rpa_python.txt')
    return int(_tagui_output())


def title():
    if not _started():
        show_error('[RPA][ERROR] - use init() before using title()')
        return ''

    if not _chrome():
        show_error('[RPA][ERROR] - title() requires init(chrome_browser = True)')
        return ''

    send('dump title() to rpa_python.txt')
    title_result = _tagui_output()
    return title_result


def text():
    if not _started():
        show_error('[RPA][ERROR] - use init() before using text()')
        return ''

    if not _chrome():
        show_error('[RPA][ERROR] - text() requires init(chrome_browser = True)')
        return ''

    send('dump text() to rpa_python.txt')
    text_result = _tagui_output()
    return text_result


def timer():
    if not _started():
        show_error('[RPA][ERROR] - use init() before using timer()')
        return float(0)

    send('dump timer() to rpa_python.txt')
    timer_result = _tagui_output()
    return float(timer_result)


def mouse_xy():
    if not _started():
        show_error('[RPA][ERROR] - use init() before using mouse_xy()')
        return ''

    if not _visual():
        show_error('[RPA][ERROR] - mouse_xy() requires init(visual_automation = True)')
        return ''

    send('dump mouse_xy() to rpa_python.txt')
    mouse_xy_result = _tagui_output()
    return mouse_xy_result


def mouse_x():
    if not _started():
        show_error('[RPA][ERROR] - use init() before using mouse_x()')
        return int(0)

    if not _visual():
        show_error('[RPA][ERROR] - mouse_x() requires init(visual_automation = True)')
        return int(0)

    send('dump mouse_x() to rpa_python.txt')
    mouse_x_result = _tagui_output()
    return int(mouse_x_result)


def mouse_y():
    if not _started():
        show_error('[RPA][ERROR] - use init() before using mouse_y()')
        return int(0)

    if not _visual():
        show_error('[RPA][ERROR] - mouse_y() requires init(visual_automation = True)')
        return int(0)

    send('dump mouse_y() to rpa_python.txt')
    mouse_y_result = _tagui_output()
    return int(mouse_y_result)


def clipboard(text_to_put=None):
    if not _started():
        show_error('[RPA][ERROR] - use init() before using clipboard()')
        return False

    if not _visual():
        show_error('[RPA][ERROR] - clipboard() requires init(visual_automation = True)')
        return False

    if text_to_put is None:
        send('dump clipboard() to rpa_python.txt')
        clipboard_result = _tagui_output()
        return clipboard_result

    elif not send("js clipboard('" + text_to_put.replace("'", '[BACKSLASH_QUOTE]') + "')"):
        return False

    else:
        return True


def download_location(location=None):
    global _tagui_download_directory
    if not _started():
        show_error('[RPA][ERROR] - use init() before using download_location()')
        return False

    if location is None:
        return _tagui_download_directory

    if "'" in location:
        show_error('[RPA][ERROR] - single quote in location not supported here')
        return False

    if platform.system() == 'Windows':
        location = location.replace('/', '\\')

    if not send("chrome_step('Page.setDownloadBehavior',{behavior: 'allow', downloadPath: '" + location + "'});"):
        return False

    else:
        _tagui_download_directory = location
        return True


def get_text(source_text=None, left=None, right=None, count=1):
    if source_text is None or left is None or right is None:
        return ''

    left_position = source_text.find(left)
    if left_position == -1: return ''
    right_position = source_text.find(right, left_position + 1)
    if right_position == -1: return ''

    if count > 1:
        occurrence_count = 2
        while occurrence_count <= count:
            occurrence_count += 1
            left_position = source_text.find(left, right_position + 1)
            if left_position == -1: return ''
            right_position = source_text.find(right, left_position + 1)
            if right_position == -1: return ''

    return source_text[left_position + len(left): right_position].strip()


def del_chars(source_text=None, characters=None):
    if source_text is None:
        return ''

    elif characters is None:
        return source_text

    for character in characters:
        source_text = source_text.replace(character, '')

    return source_text

def test_generator_to_async_generator():
    """
    Test conversion of sync to async generator.
    This should run the synchronous parts in a background thread.
    """
    async_gen = generator_to_async_generator(_sync_generator)

    items = []

    async def consume_async_generator():
        async for item in async_gen:
            items.append(item)

    # Run the event loop until all items are collected.
    run(consume_async_generator())
    assert items == [1, 10]

def test_cursor_up(_buffer):
    # Cursor up to a line thats longer.
    _buffer.insert_text("long line1\nline2")
    _buffer.cursor_up()

    assert _buffer.document.cursor_position == 5

    # Going up when already at the top.
    _buffer.cursor_up()
    assert _buffer.document.cursor_position == 5

    # Going up to a line that's shorter.
    _buffer.reset()
    _buffer.insert_text("line1\nlong line2")

    _buffer.cursor_up()
    assert _buffer.document.cursor_position == 5


def test_cursor_down(_buffer):
    _buffer.insert_text("line1\nline2")
    _buffer.cursor_position = 3

    # Normally going down
    _buffer.cursor_down()
    assert _buffer.document.cursor_position == len("line1\nlin")

    # Going down to a line that's shorter.
    _buffer.reset()
    _buffer.insert_text("long line1\na\nb")
    _buffer.cursor_position = 3

    _buffer.cursor_down()
    assert _buffer.document.cursor_position == len("long line1\na")


def test_join_next_line(_buffer):
    _buffer.insert_text("line1\nline2\nline3")
    _buffer.cursor_up()
    _buffer.join_next_line()

    assert _buffer.text == "line1\nline2 line3"

    # Test when there is no '\n' in the text
    _buffer.reset()
    _buffer.insert_text("line1")
    _buffer.cursor_position = 0
    _buffer.join_next_line()

    assert _buffer.text == "line1"


def _feed_cli_with_input(
    text,
    editing_mode=EditingMode.EMACS,
    clipboard=None,
    history=None,
    multiline=False,
    check_line_ending=True,
    key_bindings=None,
):
    """
    Create a Prompt, feed it with the given user input and return the CLI
    object.

    This returns a (result, Application) tuple.
    """
    # If the given text doesn't end with a newline, the interface won't finish.
    if check_line_ending:
        assert text.endswith("\r")

    with create_pipe_input() as inp:
        inp.send_text(text)
        session = PromptSession(
            input=inp,
            output=DummyOutput(),
            editing_mode=editing_mode,
            history=history,
            multiline=multiline,
            clipboard=clipboard,
            key_bindings=key_bindings,
        )

        _ = session.prompt()
        return session.default_buffer.document, session.app


def test_emacs_cursor_movements():
    """
    Test cursor movements with Emacs key bindings.
    """
    # ControlA (beginning-of-line)
    result, cli = _feed_cli_with_input("hello\x01X\r")
    assert result.text == "Xhello"

    # ControlE (end-of-line)
    result, cli = _feed_cli_with_input("hello\x01X\x05Y\r")
    assert result.text == "XhelloY"

    # ControlH or \b
    result, cli = _feed_cli_with_input("hello\x08X\r")
    assert result.text == "hellX"

    # Delete.  (Left, left, delete)
    result, cli = _feed_cli_with_input("hello\x1b[D\x1b[D\x1b[3~\r")
    assert result.text == "helo"

    # Left.
    result, cli = _feed_cli_with_input("hello\x1b[DX\r")
    assert result.text == "hellXo"

    # ControlA, right
    result, cli = _feed_cli_with_input("hello\x01\x1b[CX\r")
    assert result.text == "hXello"

    # ControlB (backward-char)
    result, cli = _feed_cli_with_input("hello\x02X\r")
    assert result.text == "hellXo"

    # ControlF (forward-char)
    result, cli = _feed_cli_with_input("hello\x01\x06X\r")
    assert result.text == "hXello"

    # ControlD: delete after cursor.
    result, cli = _feed_cli_with_input("hello\x01\x04\r")
    assert result.text == "ello"

    # ControlD at the end of the input ssshould not do anything.
    result, cli = _feed_cli_with_input("hello\x04\r")
    assert result.text == "hello"

    # Left, Left, ControlK  (kill-line)
    result, cli = _feed_cli_with_input("hello\x1b[D\x1b[D\x0b\r")
    assert result.text == "hel"

    # Left, Left Esc- ControlK (kill-line, but negative)
    result, cli = _feed_cli_with_input("hello\x1b[D\x1b[D\x1b-\x0b\r")
    assert result.text == "lo"

    # ControlL: should not influence the result.
    result, cli = _feed_cli_with_input("hello\x0c\r")
    assert result.text == "hello"

    # ControlRight (forward-word)
    result, cli = _feed_cli_with_input("hello world\x01X\x1b[1;5CY\r")
    assert result.text == "XhelloY world"

    # ContrlolLeft (backward-word)
    result, cli = _feed_cli_with_input("hello world\x1b[1;5DY\r")
    assert result.text == "hello Yworld"

    # <esc>-f with argument. (forward-word)
    result, cli = _feed_cli_with_input("hello world abc def\x01\x1b3\x1bfX\r")
    assert result.text == "hello world abcX def"

    # <esc>-f with negative argument. (forward-word)
    result, cli = _feed_cli_with_input("hello world abc def\x1b-\x1b3\x1bfX\r")
    assert result.text == "hello Xworld abc def"

    # <esc>-b with argument. (backward-word)
    result, cli = _feed_cli_with_input("hello world abc def\x1b3\x1bbX\r")
    assert result.text == "hello Xworld abc def"

    # <esc>-b with negative argument. (backward-word)
    result, cli = _feed_cli_with_input("hello world abc def\x01\x1b-\x1b3\x1bbX\r")
    assert result.text == "hello world abc Xdef"

    # ControlW (kill-word / unix-word-rubout)
    result, cli = _feed_cli_with_input("hello world\x17\r")
    assert result.text == "hello "
    assert cli.clipboard.get_data().text == "world"

    result, cli = _feed_cli_with_input("test hello world\x1b2\x17\r")
    assert result.text == "test "

    # Escape Backspace (unix-word-rubout)
    result, cli = _feed_cli_with_input("hello world\x1b\x7f\r")
    assert result.text == "hello "
    assert cli.clipboard.get_data().text == "world"

    result, cli = _feed_cli_with_input("hello world\x1b\x08\r")
    assert result.text == "hello "
    assert cli.clipboard.get_data().text == "world"

    # Backspace (backward-delete-char)
    result, cli = _feed_cli_with_input("hello world\x7f\r")
    assert result.text == "hello worl"
    assert result.cursor_position == len("hello worl")

    result, cli = _feed_cli_with_input("hello world\x08\r")
    assert result.text == "hello worl"
    assert result.cursor_position == len("hello worl")

    # Delete (delete-char)
    result, cli = _feed_cli_with_input("hello world\x01\x1b[3~\r")
    assert result.text == "ello world"
    assert result.cursor_position == 0

    # Escape-\\ (delete-horizontal-space)
    result, cli = _feed_cli_with_input("hello     world\x1b8\x02\x1b\\\r")
    assert result.text == "helloworld"
    assert result.cursor_position == len("hello")


def test_emacs_kill_multiple_words_and_paste():
    # Using control-w twice should place both words on the clipboard.
    result, cli = _feed_cli_with_input(
        "hello world test\x17\x17--\x19\x19\r"  # Twice c-w.  Twice c-y.
    )
    assert result.text == "hello --world testworld test"
    assert cli.clipboard.get_data().text == "world test"

    # Using alt-d twice should place both words on the clipboard.
    result, cli = _feed_cli_with_input(
        "hello world test"
        "\x1bb\x1bb"  # Twice left.
        "\x1bd\x1bd"  # Twice kill-word.
        "abc"
        "\x19"  # Paste.
        "\r"
    )
    assert result.text == "hello abcworld test"
    assert cli.clipboard.get_data().text == "world test"


def test_interrupts():
    # ControlC: raise KeyboardInterrupt.
    with pytest.raises(KeyboardInterrupt):
        result, cli = _feed_cli_with_input("hello\x03\r")

    with pytest.raises(KeyboardInterrupt):
        result, cli = _feed_cli_with_input("hello\x03\r")

    # ControlD without any input: raises EOFError.
    with pytest.raises(EOFError):
        result, cli = _feed_cli_with_input("\x04\r")



def test_transformations():
    # Meta-c (capitalize-word)
    result, cli = _feed_cli_with_input("hello world\01\x1bc\r")
    assert result.text == "Hello world"
    assert result.cursor_position == len("Hello")

    # Meta-u (uppercase-word)
    result, cli = _feed_cli_with_input("hello world\01\x1bu\r")
    assert result.text == "HELLO world"
    assert result.cursor_position == len("Hello")

    # Meta-u (downcase-word)
    result, cli = _feed_cli_with_input("HELLO WORLD\01\x1bl\r")
    assert result.text == "hello WORLD"
    assert result.cursor_position == len("Hello")

    # ControlT (transpose-chars)
    result, cli = _feed_cli_with_input("hello\x14\r")
    assert result.text == "helol"
    assert result.cursor_position == len("hello")

    # Left, Left, Control-T (transpose-chars)
    result, cli = _feed_cli_with_input("abcde\x1b[D\x1b[D\x14\r")
    assert result.text == "abdce"
    assert result.cursor_position == len("abcd")


def test_emacs_other_bindings():
    # Transpose characters.
    result, cli = _feed_cli_with_input("abcde\x14X\r")  # Ctrl-T
    assert result.text == "abcedX"

    # Left, Left, Transpose. (This is slightly different.)
    result, cli = _feed_cli_with_input("abcde\x1b[D\x1b[D\x14X\r")
    assert result.text == "abdcXe"

    # Clear before cursor.
    result, cli = _feed_cli_with_input("hello\x1b[D\x1b[D\x15X\r")
    assert result.text == "Xlo"

    # unix-word-rubout: delete word before the cursor.
    # (ControlW).
    result, cli = _feed_cli_with_input("hello world test\x17X\r")
    assert result.text == "hello world X"

    result, cli = _feed_cli_with_input("hello world /some/very/long/path\x17X\r")
    assert result.text == "hello world X"

    # (with argument.)
    result, cli = _feed_cli_with_input("hello world test\x1b2\x17X\r")
    assert result.text == "hello X"

    result, cli = _feed_cli_with_input("hello world /some/very/long/path\x1b2\x17X\r")
    assert result.text == "hello X"

    # backward-kill-word: delete word before the cursor.
    # (Esc-ControlH).
    result, cli = _feed_cli_with_input("hello world /some/very/long/path\x1b\x08X\r")
    assert result.text == "hello world /some/very/long/X"

    # (with arguments.)
    result, cli = _feed_cli_with_input(
        "hello world /some/very/long/path\x1b3\x1b\x08X\r"
    )
    assert result.text == "hello world /some/very/X"


def test_controlx_controlx():
    # At the end: go to the start of the line.
    result, cli = _feed_cli_with_input("hello world\x18\x18X\r")
    assert result.text == "Xhello world"
    assert result.cursor_position == 1

    # At the start: go to the end of the line.
    result, cli = _feed_cli_with_input("hello world\x01\x18\x18X\r")
    assert result.text == "hello worldX"

    # Left, Left Control-X Control-X: go to the end of the line.
    result, cli = _feed_cli_with_input("hello world\x1b[D\x1b[D\x18\x18X\r")
    assert result.text == "hello worldX"


def test_emacs_history_bindings():
    # Adding a new item to the history.
    history = _history()
    result, cli = _feed_cli_with_input("new input\r", history=history)
    assert result.text == "new input"
    history.get_strings()[-1] == "new input"

    # Go up in history, and accept the last item.
    result, cli = _feed_cli_with_input("hello\x1b[A\r", history=history)
    assert result.text == "new input"

    # Esc< (beginning-of-history)
    result, cli = _feed_cli_with_input("hello\x1b<\r", history=history)
    assert result.text == "line1 first input"

    # Esc> (end-of-history)
    result, cli = _feed_cli_with_input(
        "another item\x1b[A\x1b[a\x1b>\r", history=history
    )
    assert result.text == "another item"

    # ControlUp (previous-history)
    result, cli = _feed_cli_with_input("\x1b[1;5A\r", history=history)
    assert result.text == "another item"

    # Esc< ControlDown (beginning-of-history, next-history)
    result, cli = _feed_cli_with_input("\x1b<\x1b[1;5B\r", history=history)
    assert result.text == "line2 second input"

def test_emacs_arguments():
    """
    Test various combinations of arguments in Emacs mode.
    """
    # esc 4
    result, cli = _feed_cli_with_input("\x1b4x\r")
    assert result.text == "xxxx"

    # esc 4 4
    result, cli = _feed_cli_with_input("\x1b44x\r")
    assert result.text == "x" * 44

    # esc 4 esc 4
    result, cli = _feed_cli_with_input("\x1b4\x1b4x\r")
    assert result.text == "x" * 44

    # esc - right (-1 position to the right, equals 1 to the left.)
    result, cli = _feed_cli_with_input("aaaa\x1b-\x1b[Cbbbb\r")
    assert result.text == "aaabbbba"

    # esc - 3 right
    result, cli = _feed_cli_with_input("aaaa\x1b-3\x1b[Cbbbb\r")
    assert result.text == "abbbbaaa"

    # esc - - - 3 right
    result, cli = _feed_cli_with_input("aaaa\x1b---3\x1b[Cbbbb\r")
    assert result.text == "abbbbaaa"


def test_emacs_arguments_for_all_commands():
    """
    Test all Emacs commands with Meta-[0-9] arguments (both positive and
    negative). No one should crash.
    """
    for key in ANSI_SEQUENCES:
        # Ignore BracketedPaste. This would hang forever, because it waits for
        # the end sequence.
        if key != "\x1b[200~":
            try:
                # Note: we add an 'X' after the key, because Ctrl-Q (quoted-insert)
                # expects something to follow. We add an additional \r, because
                # Ctrl-R and Ctrl-S (reverse-search) expect that.
                result, cli = _feed_cli_with_input("hello\x1b4" + key + "X\r\r")

                result, cli = _feed_cli_with_input("hello\x1b-" + key + "X\r\r")
            except KeyboardInterrupt:
                # This exception should only be raised for Ctrl-C
                assert key == "\x03"


def test_emacs_kill_ring():
    operations = (
        # abc ControlA ControlK
        "abc\x01\x0b"
        # def ControlA ControlK
        "def\x01\x0b"
        # ghi ControlA ControlK
        "ghi\x01\x0b"
        # ControlY (yank)
        "\x19"
    )

    result, cli = _feed_cli_with_input(operations + "\r")
    assert result.text == "ghi"

    result, cli = _feed_cli_with_input(operations + "\x1by\r")
    assert result.text == "def"

    result, cli = _feed_cli_with_input(operations + "\x1by\x1by\r")
    assert result.text == "abc"

    result, cli = _feed_cli_with_input(operations + "\x1by\x1by\x1by\r")
    assert result.text == "ghi"


def test_emacs_selection():
    # Copy/paste empty selection should not do anything.
    operations = (
        "hello"
        # Twice left.
        "\x1b[D\x1b[D"
        # Control-Space
        "\x00"
        # ControlW (cut)
        "\x17"
        # ControlY twice. (paste twice)
        "\x19\x19\r"
    )

    result, cli = _feed_cli_with_input(operations)
    assert result.text == "hello"

    # Copy/paste one character.
    operations = (
        "hello"
        # Twice left.
        "\x1b[D\x1b[D"
        # Control-Space
        "\x00"
        # Right.
        "\x1b[C"
        # ControlW (cut)
        "\x17"
        # ControlA (Home).
        "\x01"
        # ControlY (paste)
        "\x19\r"
    )

    result, cli = _feed_cli_with_input(operations)
    assert result.text == "lhelo"

def test_emacs_nested_macro():
    "Test calling the macro within a macro."
    # Calling a macro within a macro should take the previous recording (if one
    # exists), not the one that is in progress.
    operations = (
        "\x18("  # Start recording macro. C-X(
        "hello"
        "\x18e"  # Execute macro.
        "\x18)"  # Stop recording macro.
        "\x18e"  # Execute macro.
        "\r"
    )

    result, cli = _feed_cli_with_input(operations)
    assert result.text == "hellohello"

    operations = (
        "\x18("  # Start recording macro. C-X(
        "hello"
        "\x18)"  # Stop recording macro.
        "\x18("  # Start recording macro. C-X(
        "\x18e"  # Execute macro.
        "world"
        "\x18)"  # Stop recording macro.
        "\x01\x0b"  # Delete all (c-a c-k).
        "\x18e"  # Execute macro.
        "\r"
    )

    result, cli = _feed_cli_with_input(operations)
    assert result.text == "helloworld"

def test_vi_cursor_movements():
    """
    Test cursor movements with Vi key bindings.
    """
    feed = partial(_feed_cli_with_input, editing_mode=EditingMode.VI)

    result, cli = feed("\x1b\r")
    assert result.text == ""
    assert cli.editing_mode == EditingMode.VI

    # Esc h a X
    result, cli = feed("hello\x1bhaX\r")
    assert result.text == "hellXo"

    # Esc I X
    result, cli = feed("hello\x1bIX\r")
    assert result.text == "Xhello"

    # Esc I X
    result, cli = feed("hello\x1bIX\r")
    assert result.text == "Xhello"

    # Esc 2hiX
    result, cli = feed("hello\x1b2hiX\r")
    assert result.text == "heXllo"

    # Esc 2h2liX
    result, cli = feed("hello\x1b2h2liX\r")
    assert result.text == "hellXo"

    # Esc \b\b
    result, cli = feed("hello\b\b\r")
    assert result.text == "hel"

    # Esc \b\b
    result, cli = feed("hello\b\b\r")
    assert result.text == "hel"

    # Esc 2h D
    result, cli = feed("hello\x1b2hD\r")
    assert result.text == "he"

    # Esc 2h rX \r
    result, cli = feed("hello\x1b2hrX\r")
    assert result.text == "heXlo"


def test_vi_text_objects():
    feed = partial(_feed_cli_with_input, editing_mode=EditingMode.VI)

    # Esc gUgg
    result, cli = feed("hello\x1bgUgg\r")
    assert result.text == "HELLO"

    # Esc gUU
    result, cli = feed("hello\x1bgUU\r")
    assert result.text == "HELLO"

    # Esc di(
    result, cli = feed("before(inside)after\x1b8hdi(\r")
    assert result.text == "before()after"

    # Esc di[
    result, cli = feed("before[inside]after\x1b8hdi[\r")
    assert result.text == "before[]after"

    # Esc da(
    result, cli = feed("before(inside)after\x1b8hda(\r")
    assert result.text == "beforeafter"


def test_vi_digraphs():
    feed = partial(_feed_cli_with_input, editing_mode=EditingMode.VI)

    # C-K o/
    result, cli = feed("hello\x0bo/\r")
    assert result.text == "helloø"

    # C-K /o  (reversed input.)
    result, cli = feed("hello\x0b/o\r")
    assert result.text == "helloø"

    # C-K e:
    result, cli = feed("hello\x0be:\r")
    assert result.text == "helloë"

    # C-K xxy (Unknown digraph.)
    result, cli = feed("hello\x0bxxy\r")
    assert result.text == "helloy"


def test_vi_block_editing():
    "Test Vi Control-V style block insertion."
    feed = partial(_feed_cli_with_input, editing_mode=EditingMode.VI, multiline=True)

    operations = (
        # Six lines of text.
        "-line1\r-line2\r-line3\r-line4\r-line5\r-line6"
        # Go to the second character of the second line.
        "\x1bkkkkkkkj0l"
        # Enter Visual block mode.
        "\x16"
        # Go down two more lines.
        "jj"
        # Go 3 characters to the right.
        "lll"
        # Go to insert mode.
        "insert"  # (Will be replaced.)
        # Insert stars.
        "***"
        # Escape again.
        "\x1b\r"
    )

    # Control-I
    result, cli = feed(operations.replace("insert", "I"))

    assert result.text == "-line1\n-***line2\n-***line3\n-***line4\n-line5\n-line6"

    # Control-A
    result, cli = feed(operations.replace("insert", "A"))

    assert result.text == "-line1\n-line***2\n-line***3\n-line***4\n-line5\n-line6"


def test_vi_block_editing_empty_lines():
    "Test block editing on empty lines."
    feed = partial(_feed_cli_with_input, editing_mode=EditingMode.VI, multiline=True)

    operations = (
        # Six empty lines.
        "\r\r\r\r\r"
        # Go to beginning of the document.
        "\x1bgg"
        # Enter Visual block mode.
        "\x16"
        # Go down two more lines.
        "jj"
        # Go 3 characters to the right.
        "lll"
        # Go to insert mode.
        "insert"  # (Will be replaced.)
        # Insert stars.
        "***"
        # Escape again.
        "\x1b\r"
    )

    # Control-I
    result, cli = feed(operations.replace("insert", "I"))

    assert result.text == "***\n***\n***\n\n\n"

    # Control-A
    result, cli = feed(operations.replace("insert", "A"))

    assert result.text == "***\n***\n***\n\n\n"


def test_vi_visual_line_copy():
    feed = partial(_feed_cli_with_input, editing_mode=EditingMode.VI, multiline=True)

    operations = (
        # Three lines of text.
        "-line1\r-line2\r-line3\r-line4\r-line5\r-line6"
        # Go to the second character of the second line.
        "\x1bkkkkkkkj0l"
        # Enter Visual linemode.
        "V"
        # Go down one line.
        "j"
        # Go 3 characters to the right (should not do much).
        "lll"
        # Copy this block.
        "y"
        # Go down one line.
        "j"
        # Insert block twice.
        "2p"
        # Escape again.
        "\x1b\r"
    )

    result, cli = feed(operations)

    assert (
        result.text
        == "-line1\n-line2\n-line3\n-line4\n-line2\n-line3\n-line2\n-line3\n-line5\n-line6"
    )


def test_vi_visual_empty_line():
    """
    Test edge case with an empty line in Visual-line mode.
    """
    feed = partial(_feed_cli_with_input, editing_mode=EditingMode.VI, multiline=True)

    # 1. Delete first two lines.
    operations = (
        # Three lines of text. The middle one is empty.
        "hello\r\rworld"
        # Go to the start.
        "\x1bgg"
        # Visual line and move down.
        "Vj"
        # Delete.
        "d\r"
    )
    result, cli = feed(operations)
    assert result.text == "world"

    # 1. Delete middle line.
    operations = (
        # Three lines of text. The middle one is empty.
        "hello\r\rworld"
        # Go to middle line.
        "\x1bggj"
        # Delete line
        "Vd\r"
    )

    result, cli = feed(operations)
    assert result.text == "hello\nworld"


def test_vi_character_delete_after_cursor():
    "Test 'x' keypress."
    feed = partial(_feed_cli_with_input, editing_mode=EditingMode.VI, multiline=True)

    # Delete one character.
    result, cli = feed("abcd\x1bHx\r")
    assert result.text == "bcd"

    # Delete multiple character.s
    result, cli = feed("abcd\x1bH3x\r")
    assert result.text == "d"

    # Delete on empty line.
    result, cli = feed("\x1bo\x1bo\x1bggx\r")
    assert result.text == "\n\n"

    # Delete multiple on empty line.
    result, cli = feed("\x1bo\x1bo\x1bgg10x\r")
    assert result.text == "\n\n"

    # Delete multiple on empty line.
    result, cli = feed("hello\x1bo\x1bo\x1bgg3x\r")
    assert result.text == "lo\n\n"


def test_vi_character_delete_before_cursor():
    "Test 'X' keypress."
    feed = partial(_feed_cli_with_input, editing_mode=EditingMode.VI, multiline=True)

    # Delete one character.
    result, cli = feed("abcd\x1bX\r")
    assert result.text == "abd"

    # Delete multiple character.
    result, cli = feed("hello world\x1b3X\r")
    assert result.text == "hello wd"

    # Delete multiple character on multiple lines.
    result, cli = feed("hello\x1boworld\x1bgg$3X\r")
    assert result.text == "ho\nworld"

    result, cli = feed("hello\x1boworld\x1b100X\r")
    assert result.text == "hello\nd"

    # Delete on empty line.
    result, cli = feed("\x1bo\x1bo\x1b10X\r")
    assert result.text == "\n\n"


def test_vi_character_paste():
    feed = partial(_feed_cli_with_input, editing_mode=EditingMode.VI)

    # Test 'p' character paste.
    result, cli = feed("abcde\x1bhhxp\r")
    assert result.text == "abdce"
    assert result.cursor_position == 3

    # Test 'P' character paste.
    result, cli = feed("abcde\x1bhhxP\r")
    assert result.text == "abcde"
    assert result.cursor_position == 2


def test_vi_temp_navigation_mode():
    """
    Test c-o binding: go for one action into navigation mode.
    """
    feed = partial(_feed_cli_with_input, editing_mode=EditingMode.VI)

    result, cli = feed("abcde" "\x0f" "3h" "x\r")  # c-o  # 3 times to the left.
    assert result.text == "axbcde"
    assert result.cursor_position == 2

    result, cli = feed("abcde" "\x0f" "b" "x\r")  # c-o  # One word backwards.
    assert result.text == "xabcde"
    assert result.cursor_position == 1

    # In replace mode
    result, cli = feed(
        "abcdef"
        "\x1b"  # Navigation mode.
        "0l"  # Start of line, one character to the right.
        "R"  # Replace mode
        "78"
        "\x0f"  # c-o
        "l"  # One character forwards.
        "9\r"
    )
    assert result.text == "a78d9f"
    assert result.cursor_position == 5


def test_vi_macros():
    feed = partial(_feed_cli_with_input, editing_mode=EditingMode.VI)

    # Record and execute macro.
    result, cli = feed("\x1bqcahello\x1bq@c\r")
    assert result.text == "hellohello"
    assert result.cursor_position == 9

    # Running unknown macro.
    result, cli = feed("\x1b@d\r")
    assert result.text == ""
    assert result.cursor_position == 0

    # When a macro is called within a macro.
    # It shouldn't result in eternal recursion.
    result, cli = feed("\x1bqxahello\x1b@xq@x\r")
    assert result.text == "hellohello"
    assert result.cursor_position == 9

    # Nested macros.
    result, cli = feed(
        # Define macro 'x'.
        "\x1bqxahello\x1bq"
        # Define macro 'y' which calls 'x'.
        "qya\x1b@xaworld\x1bq"
        # Delete line.
        "2dd"
        # Execute 'y'
        "@y\r"
    )

    assert result.text == "helloworld"


def test_accept_default():
    """
    Test `prompt(accept_default=True)`.
    """
    with create_pipe_input() as inp:
        session = PromptSession(input=inp, output=DummyOutput())
        result = session.prompt(default="hello", accept_default=True)
        assert result == "hello"

        # Test calling prompt() for a second time. (We had an issue where the
        # prompt reset between calls happened at the wrong time, breaking this.)
        result = session.prompt(default="world", accept_default=True)
        assert result == "world"

def test_pathcompleter_completes_files_in_current_directory():
    # setup: create a test dir with 10 files
    test_dir = tempfile.mkdtemp()
    write_test_files(test_dir)

    expected = sorted(str(i) for i in range(10))

    if not test_dir.endswith(os.path.sep):
        test_dir += os.path.sep

    with chdir(test_dir):
        completer = PathCompleter()
        # this should complete on the cwd
        doc_text = ""
        doc = Document(doc_text, len(doc_text))
        event = CompleteEvent()
        completions = list(completer.get_completions(doc, event))
        result = sorted(c.text for c in completions)
        assert expected == result

    # cleanup
    shutil.rmtree(test_dir)


def test_pathcompleter_completes_files_in_absolute_directory():
    # setup: create a test dir with 10 files
    test_dir = tempfile.mkdtemp()
    write_test_files(test_dir)

    expected = sorted(str(i) for i in range(10))

    test_dir = os.path.abspath(test_dir)
    if not test_dir.endswith(os.path.sep):
        test_dir += os.path.sep

    completer = PathCompleter()
    # force unicode
    doc_text = str(test_dir)
    doc = Document(doc_text, len(doc_text))
    event = CompleteEvent()
    completions = list(completer.get_completions(doc, event))
    result = sorted(c.text for c in completions)
    assert expected == result

    # cleanup
    shutil.rmtree(test_dir)


def test_pathcompleter_completes_directories_with_only_directories():
    # setup: create a test dir with 10 files
    test_dir = tempfile.mkdtemp()
    write_test_files(test_dir)

    # create a sub directory there
    os.mkdir(os.path.join(test_dir, "subdir"))

    if not test_dir.endswith(os.path.sep):
        test_dir += os.path.sep

    with chdir(test_dir):
        completer = PathCompleter(only_directories=True)
        doc_text = ""
        doc = Document(doc_text, len(doc_text))
        event = CompleteEvent()
        completions = list(completer.get_completions(doc, event))
        result = [c.text for c in completions]
        assert ["subdir"] == result

    # check that there is no completion when passing a file
    with chdir(test_dir):
        completer = PathCompleter(only_directories=True)
        doc_text = "1"
        doc = Document(doc_text, len(doc_text))
        event = CompleteEvent()
        completions = list(completer.get_completions(doc, event))
        assert [] == completions

    # cleanup
    shutil.rmtree(test_dir)


def test_pathcompleter_respects_completions_under_min_input_len():
    # setup: create a test dir with 10 files
    test_dir = tempfile.mkdtemp()
    write_test_files(test_dir)

    # min len:1 and no text
    with chdir(test_dir):
        completer = PathCompleter(min_input_len=1)
        doc_text = ""
        doc = Document(doc_text, len(doc_text))
        event = CompleteEvent()
        completions = list(completer.get_completions(doc, event))
        assert [] == completions

    # min len:1 and text of len 1
    with chdir(test_dir):
        completer = PathCompleter(min_input_len=1)
        doc_text = "1"
        doc = Document(doc_text, len(doc_text))
        event = CompleteEvent()
        completions = list(completer.get_completions(doc, event))
        result = [c.text for c in completions]
        assert [""] == result

    # min len:0 and text of len 2
    with chdir(test_dir):
        completer = PathCompleter(min_input_len=0)
        doc_text = "1"
        doc = Document(doc_text, len(doc_text))
        event = CompleteEvent()
        completions = list(completer.get_completions(doc, event))
        result = [c.text for c in completions]
        assert [""] == result

    # create 10 files with a 2 char long name
    for i in range(10):
        with open(os.path.join(test_dir, str(i) * 2), "wb") as out:
            out.write(b"")

    # min len:1 and text of len 1
    with chdir(test_dir):
        completer = PathCompleter(min_input_len=1)
        doc_text = "2"
        doc = Document(doc_text, len(doc_text))
        event = CompleteEvent()
        completions = list(completer.get_completions(doc, event))
        result = sorted(c.text for c in completions)
        assert ["", "2"] == result

    # min len:2 and text of len 1
    with chdir(test_dir):
        completer = PathCompleter(min_input_len=2)
        doc_text = "2"
        doc = Document(doc_text, len(doc_text))
        event = CompleteEvent()
        completions = list(completer.get_completions(doc, event))
        assert [] == completions

    # cleanup
    shutil.rmtree(test_dir)


def test_pathcompleter_can_apply_file_filter():
    # setup: create a test dir with 10 files
    test_dir = tempfile.mkdtemp()
    write_test_files(test_dir)

    # add a .csv file
    with open(os.path.join(test_dir, "my.csv"), "wb") as out:
        out.write(b"")

    file_filter = lambda f: f and f.endswith(".csv")

    with chdir(test_dir):
        completer = PathCompleter(file_filter=file_filter)
        doc_text = ""
        doc = Document(doc_text, len(doc_text))
        event = CompleteEvent()
        completions = list(completer.get_completions(doc, event))
        result = [c.text for c in completions]
        assert ["my.csv"] == result

    # cleanup
    shutil.rmtree(test_dir)


def test_pathcompleter_get_paths_constrains_path():
    # setup: create a test dir with 10 files
    test_dir = tempfile.mkdtemp()
    write_test_files(test_dir)

    # add a subdir with 10 other files with different names
    subdir = os.path.join(test_dir, "subdir")
    os.mkdir(subdir)
    write_test_files(subdir, "abcdefghij")

    get_paths = lambda: ["subdir"]

    with chdir(test_dir):
        completer = PathCompleter(get_paths=get_paths)
        doc_text = ""
        doc = Document(doc_text, len(doc_text))
        event = CompleteEvent()
        completions = list(completer.get_completions(doc, event))
        result = [c.text for c in completions]
        expected = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]
        assert expected == result

    # cleanup
    shutil.rmtree(test_dir)


def test_word_completer_static_word_list():
    completer = WordCompleter(["abc", "def", "aaa"])

    # Static list on empty input.
    completions = completer.get_completions(Document(""), CompleteEvent())
    assert [c.text for c in completions] == ["abc", "def", "aaa"]

    # Static list on non-empty input.
    completions = completer.get_completions(Document("a"), CompleteEvent())
    assert [c.text for c in completions] == ["abc", "aaa"]

    completions = completer.get_completions(Document("A"), CompleteEvent())
    assert [c.text for c in completions] == []

    # Multiple words ending with space. (Accept all options)
    completions = completer.get_completions(Document("test "), CompleteEvent())
    assert [c.text for c in completions] == ["abc", "def", "aaa"]

    # Multiple words. (Check last only.)
    completions = completer.get_completions(Document("test a"), CompleteEvent())
    assert [c.text for c in completions] == ["abc", "aaa"]


def test_word_completer_sentence():
    # With sentence=True
    completer = WordCompleter(
        ["hello world", "www", "hello www", "hello there"], sentence=True
    )
    completions = completer.get_completions(Document("hello w"), CompleteEvent())
    assert [c.text for c in completions] == ["hello world", "hello www"]

    # With sentence=False
    completer = WordCompleter(
        ["hello world", "www", "hello www", "hello there"], sentence=False
    )
    completions = completer.get_completions(Document("hello w"), CompleteEvent())
    assert [c.text for c in completions] == ["www"]


def test_word_completer_dynamic_word_list():
    called = [0]

    def get_words():
        called[0] += 1
        return ["abc", "def", "aaa"]

    completer = WordCompleter(get_words)

    # Dynamic list on empty input.
    completions = completer.get_completions(Document(""), CompleteEvent())
    assert [c.text for c in completions] == ["abc", "def", "aaa"]
    assert called[0] == 1

    # Static list on non-empty input.
    completions = completer.get_completions(Document("a"), CompleteEvent())
    assert [c.text for c in completions] == ["abc", "aaa"]
    assert called[0] == 2


def test_word_completer_pattern():
    # With a pattern which support '.'
    completer = WordCompleter(
        ["abc", "a.b.c", "a.b", "xyz"],
        pattern=re.compile(r"^([a-zA-Z0-9_.]+|[^a-zA-Z0-9_.\s]+)"),
    )
    completions = completer.get_completions(Document("a."), CompleteEvent())
    assert [c.text for c in completions] == ["a.b.c", "a.b"]

    # Without pattern
    completer = WordCompleter(["abc", "a.b.c", "a.b", "xyz"])
    completions = completer.get_completions(Document("a."), CompleteEvent())
    assert [c.text for c in completions] == []


def test_fuzzy_completer():
    collection = [
        "migrations.py",
        "django_migrations.py",
        "django_admin_log.py",
        "api_user.doc",
        "user_group.doc",
        "users.txt",
        "accounts.txt",
        "123.py",
        "test123test.py",
    ]
    completer = FuzzyWordCompleter(collection)
    completions = completer.get_completions(Document("txt"), CompleteEvent())
    assert [c.text for c in completions] == ["users.txt", "accounts.txt"]

    completions = completer.get_completions(Document("djmi"), CompleteEvent())
    assert [c.text for c in completions] == [
        "django_migrations.py",
        "django_admin_log.py",
    ]

    completions = completer.get_completions(Document("mi"), CompleteEvent())
    assert [c.text for c in completions] == [
        "migrations.py",
        "django_migrations.py",
        "django_admin_log.py",
    ]

    completions = completer.get_completions(Document("user"), CompleteEvent())
    assert [c.text for c in completions] == [
        "user_group.doc",
        "users.txt",
        "api_user.doc",
    ]

    completions = completer.get_completions(Document("123"), CompleteEvent())
    assert [c.text for c in completions] == ["123.py", "test123test.py"]

    completions = completer.get_completions(Document("miGr"), CompleteEvent())
    assert [c.text for c in completions] == [
        "migrations.py",
        "django_migrations.py",
    ]

    # Multiple words ending with space. (Accept all options)
    completions = completer.get_completions(Document("test "), CompleteEvent())
    assert [c.text for c in completions] == collection

    # Multiple words. (Check last only.)
    completions = completer.get_completions(Document("test txt"), CompleteEvent())
    assert [c.text for c in completions] == ["users.txt", "accounts.txt"]


def test_nested_completer():
    completer = NestedCompleter.from_nested_dict(
        {
            "show": {
                "version": None,
                "clock": None,
                "interfaces": None,
                "ip": {"interface": {"brief"}},
            },
            "exit": None,
        }
    )

    # Empty input.
    completions = completer.get_completions(Document(""), CompleteEvent())
    assert {c.text for c in completions} == {"show", "exit"}

    # One character.
    completions = completer.get_completions(Document("s"), CompleteEvent())
    assert {c.text for c in completions} == {"show"}

    # One word.
    completions = completer.get_completions(Document("show"), CompleteEvent())
    assert {c.text for c in completions} == {"show"}

    # One word + space.
    completions = completer.get_completions(Document("show "), CompleteEvent())
    assert {c.text for c in completions} == {"version", "clock", "interfaces", "ip"}

    # One word + space + one character.
    completions = completer.get_completions(Document("show i"), CompleteEvent())
    assert {c.text for c in completions} == {"ip", "interfaces"}

    # One space + one word + space + one character.
    completions = completer.get_completions(Document(" show i"), CompleteEvent())
    assert {c.text for c in completions} == {"ip", "interfaces"}

    # Test nested set.
    completions = completer.get_completions(
        Document("show ip interface br"), CompleteEvent()
    )
    assert {c.text for c in completions} == {"brief"}


def test_deduplicate_completer():
    def create_completer(deduplicate: bool):
        return merge_completers(
            [
                WordCompleter(["hello", "world", "abc", "def"]),
                WordCompleter(["xyz", "xyz", "abc", "def"]),
            ],
            deduplicate=deduplicate,
        )

    completions = list(
        create_completer(deduplicate=False).get_completions(
            Document(""), CompleteEvent()
        )
    )
    assert len(completions) == 8

    completions = list(
        create_completer(deduplicate=True).get_completions(
            Document(""), CompleteEvent()
        )
    )
    assert len(completions) == 5

def test_html_with_fg_bg():
    html = HTML('<style bg="ansired">hello</style>')
    assert to_formatted_text(html) == [
        ("bg:ansired", "hello"),
    ]

    html = HTML('<style bg="ansired" fg="#ff0000">hello</style>')
    assert to_formatted_text(html) == [
        ("fg:#ff0000 bg:ansired", "hello"),
    ]

    html = HTML(
        '<style bg="ansired" fg="#ff0000">hello <world fg="ansiblue">world</world></style>'
    )
    assert to_formatted_text(html) == [
        ("fg:#ff0000 bg:ansired", "hello "),
        ("class:world fg:ansiblue bg:ansired", "world"),
    ]


def test_ansi_formatting():
    value = ANSI("\x1b[32mHe\x1b[45mllo")

    assert to_formatted_text(value) == [
        ("ansigreen", "H"),
        ("ansigreen", "e"),
        ("ansigreen bg:ansimagenta", "l"),
        ("ansigreen bg:ansimagenta", "l"),
        ("ansigreen bg:ansimagenta", "o"),
    ]

    # Bold and italic.
    value = ANSI("\x1b[1mhe\x1b[0mllo")

    assert to_formatted_text(value) == [
        ("bold", "h"),
        ("bold", "e"),
        ("", "l"),
        ("", "l"),
        ("", "o"),
    ]

    # Zero width escapes.
    value = ANSI("ab\001cd\002ef")

    assert to_formatted_text(value) == [
        ("", "a"),
        ("", "b"),
        ("[ZeroWidthEscape]", "cd"),
        ("", "e"),
        ("", "f"),
    ]

    assert isinstance(to_formatted_text(value), FormattedText)

def test_ansi_interpolation():
    # %-style interpolation.
    value = ANSI("\x1b[1m%s\x1b[0m") % "hello\x1b"
    assert to_formatted_text(value) == [
        ("bold", "h"),
        ("bold", "e"),
        ("bold", "l"),
        ("bold", "l"),
        ("bold", "o"),
        ("bold", "?"),
    ]

    value = ANSI("\x1b[1m%s\x1b[0m") % ("\x1bhello",)
    assert to_formatted_text(value) == [
        ("bold", "?"),
        ("bold", "h"),
        ("bold", "e"),
        ("bold", "l"),
        ("bold", "l"),
        ("bold", "o"),
    ]

    value = ANSI("\x1b[32m%s\x1b[45m%s") % ("He", "\x1bllo")
    assert to_formatted_text(value) == [
        ("ansigreen", "H"),
        ("ansigreen", "e"),
        ("ansigreen bg:ansimagenta", "?"),
        ("ansigreen bg:ansimagenta", "l"),
        ("ansigreen bg:ansimagenta", "l"),
        ("ansigreen bg:ansimagenta", "o"),
    ]

    # Format function.
    value = ANSI("\x1b[32m{0}\x1b[45m{1}").format("He\x1b", "llo")
    assert to_formatted_text(value) == [
        ("ansigreen", "H"),
        ("ansigreen", "e"),
        ("ansigreen", "?"),
        ("ansigreen bg:ansimagenta", "l"),
        ("ansigreen bg:ansimagenta", "l"),
        ("ansigreen bg:ansimagenta", "o"),
    ]

    value = ANSI("\x1b[32m{a}\x1b[45m{b}").format(a="\x1bHe", b="llo")
    assert to_formatted_text(value) == [
        ("ansigreen", "?"),
        ("ansigreen", "H"),
        ("ansigreen", "e"),
        ("ansigreen bg:ansimagenta", "l"),
        ("ansigreen bg:ansimagenta", "l"),
        ("ansigreen bg:ansimagenta", "o"),
    ]

    value = ANSI("\x1b[32m{:02d}\x1b[45m{:.3f}").format(3, 3.14159)
    assert to_formatted_text(value) == [
        ("ansigreen", "0"),
        ("ansigreen", "3"),
        ("ansigreen bg:ansimagenta", "3"),
        ("ansigreen bg:ansimagenta", "."),
        ("ansigreen bg:ansimagenta", "1"),
        ("ansigreen bg:ansimagenta", "4"),
        ("ansigreen bg:ansimagenta", "2"),
    ]


def test_interpolation():
    value = Template(" {} ").format(HTML("<b>hello</b>"))

    assert to_formatted_text(value) == [
        ("", " "),
        ("class:b", "hello"),
        ("", " "),
    ]

    value = Template("a{}b{}c").format(HTML("<b>hello</b>"), "world")

    assert to_formatted_text(value) == [
        ("", "a"),
        ("class:b", "hello"),
        ("", "b"),
        ("", "world"),
        ("", "c"),
    ]


def test_html_interpolation():
    # %-style interpolation.
    value = HTML("<b>%s</b>") % "&hello"
    assert to_formatted_text(value) == [("class:b", "&hello")]

    value = HTML("<b>%s</b>") % ("<hello>",)
    assert to_formatted_text(value) == [("class:b", "<hello>")]

    value = HTML("<b>%s</b><u>%s</u>") % ("<hello>", "</world>")
    assert to_formatted_text(value) == [("class:b", "<hello>"), ("class:u", "</world>")]

    # Format function.
    value = HTML("<b>{0}</b><u>{1}</u>").format("'hello'", '"world"')
    assert to_formatted_text(value) == [("class:b", "'hello'"), ("class:u", '"world"')]

    value = HTML("<b>{a}</b><u>{b}</u>").format(a="hello", b="world")
    assert to_formatted_text(value) == [("class:b", "hello"), ("class:u", "world")]

    value = HTML("<b>{:02d}</b><u>{:.3f}</u>").format(3, 3.14159)
    assert to_formatted_text(value) == [("class:b", "03"), ("class:u", "3.142")]


def test_split_lines_3():
    "Edge cases: inputs ending with newlines."
    # -1-
    lines = list(split_lines([("class:a", "line1\nline2\n")]))

    assert lines == [
        [("class:a", "line1")],
        [("class:a", "line2")],
        [("class:a", "")],
    ]

    # -2-
    lines = list(split_lines([("class:a", "\n")]))

    assert lines == [
        [],
        [("class:a", "")],
    ]

    # -3-
    lines = list(split_lines([("class:a", "")]))

    assert lines == [
        [("class:a", "")],
    ]

    def example_create_topics(a, topics):
        """ Create topics """

        new_topics = [NewTopic(topic, num_partitions=3, replication_factor=1) for topic in topics]
        # Call create_topics to asynchronously create topics, a dict
        # of <topic,future> is returned.
        fs = a.create_topics(new_topics)

        # Wait for operation to finish.
        # Timeouts are preferably controlled by passing request_timeout=15.0
        # to the create_topics() call.
        # All futures will finish at the same time.
        for topic, f in fs.items():
            try:
                f.result()  # The result itself is None
                print("Topic {} created".format(topic))
            except Exception as e:
                print("Failed to create topic {}: {}".format(topic, e))

    def example_delete_topics(a, topics):
        """ delete topics """

        # Call delete_topics to asynchronously delete topics, a future is returned.
        # By default this operation on the broker returns immediately while
        # topics are deleted in the background. But here we give it some time (30s)
        # to propagate in the cluster before returning.
        #
        # Returns a dict of <topic,future>.
        fs = a.delete_topics(topics, operation_timeout=30)

        # Wait for operation to finish.
        for topic, f in fs.items():
            try:
                f.result()  # The result itself is None
                print("Topic {} deleted".format(topic))
            except Exception as e:
                print("Failed to delete topic {}: {}".format(topic, e))

    def example_create_partitions(a, topics):
        """ create partitions """

        new_parts = [NewPartitions(topic, int(new_total_count)) for
                     topic, new_total_count in zip(topics[0::2], topics[1::2])]

        # Try switching validate_only to True to only validate the operation
        # on the broker but not actually perform it.
        fs = a.create_partitions(new_parts, validate_only=False)

        # Wait for operation to finish.
        for topic, f in fs.items():
            try:
                f.result()  # The result itself is None
                print("Additional partitions created for topic {}".format(topic))
            except Exception as e:
                print("Failed to add partitions to topic {}: {}".format(topic, e))

    def print_config(config, depth):
        print('%40s = %-50s  [%s,is:read-only=%r,default=%r,sensitive=%r,synonym=%r,synonyms=%s]' %
              ((' ' * depth) + config.name, config.value, ConfigSource(config.source),
               config.is_read_only, config.is_default,
               config.is_sensitive, config.is_synonym,
               ["%s:%s" % (x.name, ConfigSource(x.source))
                for x in iter(config.synonyms.values())]))

    def example_describe_configs(a, args):
        """ describe configs """

        resources = [ConfigResource(restype, resname) for
                     restype, resname in zip(args[0::2], args[1::2])]

        fs = a.describe_configs(resources)

        # Wait for operation to finish.
        for res, f in fs.items():
            try:
                configs = f.result()
                for config in iter(configs.values()):
                    print_config(config, 1)

            except KafkaException as e:
                print("Failed to describe {}: {}".format(res, e))
            except Exception:
                raise

    def example_create_acls(a, args):
        """ create acls """

        acl_bindings = [
            AclBinding(
                ResourceType[restype],
                parse_nullable_string(resname),
                ResourcePatternType[resource_pattern_type],
                parse_nullable_string(principal),
                parse_nullable_string(host),
                AclOperation[operation],
                AclPermissionType[permission_type]
            )
            for restype, resname, resource_pattern_type,
            principal, host, operation, permission_type
            in zip(
                args[0::7],
                args[1::7],
                args[2::7],
                args[3::7],
                args[4::7],
                args[5::7],
                args[6::7],
            )
        ]

        try:
            fs = a.create_acls(acl_bindings, request_timeout=10)
        except ValueError as e:
            print(f"create_acls() failed: {e}")
            return

        # Wait for operation to finish.
        for res, f in fs.items():
            try:
                result = f.result()
                if result is None:
                    print("Created {}".format(res))

            except KafkaException as e:
                print("Failed to create ACL {}: {}".format(res, e))
            except Exception:
                raise

    def example_describe_acls(a, args):
        """ describe acls """

        acl_binding_filters = [
            AclBindingFilter(
                ResourceType[restype],
                parse_nullable_string(resname),
                ResourcePatternType[resource_pattern_type],
                parse_nullable_string(principal),
                parse_nullable_string(host),
                AclOperation[operation],
                AclPermissionType[permission_type]
            )
            for restype, resname, resource_pattern_type,
            principal, host, operation, permission_type
            in zip(
                args[0::7],
                args[1::7],
                args[2::7],
                args[3::7],
                args[4::7],
                args[5::7],
                args[6::7],
            )
        ]

        fs = [
            a.describe_acls(acl_binding_filter, request_timeout=10)
            for acl_binding_filter in acl_binding_filters
        ]
        # Wait for operations to finish.
        for acl_binding_filter, f in zip(acl_binding_filters, fs):
            try:
                print("Acls matching filter: {}".format(acl_binding_filter))
                acl_bindings = f.result()
                for acl_binding in acl_bindings:
                    print(acl_binding)

            except KafkaException as e:
                print("Failed to describe {}: {}".format(acl_binding_filter, e))
            except Exception:
                raise

    def example_delete_acls(a, args):
        """ delete acls """

        acl_binding_filters = [
            AclBindingFilter(
                ResourceType[restype],
                parse_nullable_string(resname),
                ResourcePatternType[resource_pattern_type],
                parse_nullable_string(principal),
                parse_nullable_string(host),
                AclOperation[operation],
                AclPermissionType[permission_type]
            )
            for restype, resname, resource_pattern_type,
            principal, host, operation, permission_type
            in zip(
                args[0::7],
                args[1::7],
                args[2::7],
                args[3::7],
                args[4::7],
                args[5::7],
                args[6::7],
            )
        ]

        try:
            fs = a.delete_acls(acl_binding_filters, request_timeout=10)
        except ValueError as e:
            print(f"delete_acls() failed: {e}")
            return

        # Wait for operation to finish.
        for res, f in fs.items():
            try:
                acl_bindings = f.result()
                print("Deleted acls matching filter: {}".format(res))
                for acl_binding in acl_bindings:
                    print(" ", acl_binding)

            except KafkaException as e:
                print("Failed to delete {}: {}".format(res, e))
            except Exception:
                raise

    def example_incremental_alter_configs(a, args):
        """ Incrementally alter configs, keeping non-specified
        configuration properties with their previous values.

        Input Format : ResourceType1 ResourceName1 Key=Operation:Value;Key2=Operation2:Value2;Key3=DELETE
        ResourceType2 ResourceName2 ...

        Example: TOPIC T1 compression.type=SET:lz4;cleanup.policy=ADD:compact;
        retention.ms=DELETE TOPIC T2 compression.type=SET:gzip ...
        """
        resources = []
        for restype, resname, configs in zip(args[0::3], args[1::3], args[2::3]):
            incremental_configs = []
            for name, operation_and_value in [conf.split('=') for conf in configs.split(';')]:
                if operation_and_value == "DELETE":
                    operation, value = operation_and_value, None
                else:
                    operation, value = operation_and_value.split(':')
                operation = AlterConfigOpType[operation]
                incremental_configs.append(ConfigEntry(name, value,
                                                       incremental_operation=operation))
            resources.append(ConfigResource(restype, resname,
                                            incremental_configs=incremental_configs))

        fs = a.incremental_alter_configs(resources)

        # Wait for operation to finish.
        for res, f in fs.items():
            try:
                f.result()  # empty, but raises exception on failure
                print("{} configuration successfully altered".format(res))
            except Exception:
                raise

    def example_alter_configs(a, args):
        """ Alter configs atomically, replacing non-specified
        configuration properties with their default values.
        """

        resources = []
        for restype, resname, configs in zip(args[0::3], args[1::3], args[2::3]):
            resource = ConfigResource(restype, resname)
            resources.append(resource)
            for k, v in [conf.split('=') for conf in configs.split(',')]:
                resource.set_config(k, v)

        fs = a.alter_configs(resources)

        # Wait for operation to finish.
        for res, f in fs.items():
            try:
                f.result()  # empty, but raises exception on failure
                print("{} configuration successfully altered".format(res))
            except Exception:
                raise

    def example_delta_alter_configs(a, args):
        """
        The AlterConfigs Kafka API requires all configuration to be passed,
        any left out configuration properties will revert to their default settings.

        This example shows how to just modify the supplied configuration entries
        by first reading the configuration from the broker, updating the supplied
        configuration with the broker configuration (without overwriting), and
        then writing it all back.

        The async nature of futures is also show-cased, which makes this example
        a bit more complex than it needs to be in the synchronous case.
        """

        # Convert supplied config to resources.
        # We can reuse the same resources both for describe_configs and
        # alter_configs.
        resources = []
        for restype, resname, configs in zip(args[0::3], args[1::3], args[2::3]):
            resource = ConfigResource(restype, resname)
            resources.append(resource)
            for k, v in [conf.split('=') for conf in configs.split(',')]:
                resource.set_config(k, v)

        # Set up a locked counter and an Event (for signaling) to track when the
        # second level of futures are done. This is a bit of contrived example
        # due to no other asynchronous mechanism being used, so we'll need
        # to wait on something to signal completion.

        class WaitZero(object):
            def __init__(self, waitcnt):
                self.cnt = waitcnt
                self.lock = threading.Lock()
                self.event = threading.Event()

            def decr(self):
                """ Decrement cnt by 1"""
                with self.lock:
                    assert self.cnt > 0
                    self.cnt -= 1
                self.event.set()

            def wait(self):
                """ Wait until cnt reaches 0 """
                self.lock.acquire()
                while self.cnt > 0:
                    self.lock.release()
                    self.event.wait()
                    self.event.clear()
                    self.lock.acquire()
                self.lock.release()

            def __len__(self):
                with self.lock:
                    return self.cnt

        wait_zero = WaitZero(len(resources))

        # Read existing configuration from cluster
        fs = a.describe_configs(resources)

        def delta_alter_configs_done(fut, resource):
            e = fut.exception()
            if e is not None:
                print("Config update for {} failed: {}".format(resource, e))
            else:
                print("Config for {} updated".format(resource))
            wait_zero.decr()

        def delta_alter_configs(resource, remote_config):
            print("Updating {} supplied config entries {} with {} config entries read from cluster".format(
                len(resource), resource, len(remote_config)))
            # Only set configuration that is not default
            for k, entry in [(k, v) for k, v in remote_config.items() if not v.is_default]:
                resource.set_config(k, entry.value, overwrite=False)

            fs = a.alter_configs([resource])
            fs[resource].add_done_callback(lambda fut: delta_alter_configs_done(fut, resource))

        # For each resource's future set up a completion callback
        # that in turn calls alter_configs() on that single resource.
        # This is ineffective since the resources can usually go in
        # one single alter_configs() call, but we're also show-casing
        # the futures here.
        for res, f in fs.items():
            f.add_done_callback(lambda fut, resource=res: delta_alter_configs(resource, fut.result()))

        # Wait for done callbacks to be triggered and operations to complete.
        print("Waiting for {} resource updates to finish".format(len(wait_zero)))
        wait_zero.wait()

    def example_list(a, args):
        """ list topics, groups and cluster metadata """

        if len(args) == 0:
            what = "all"
        else:
            what = args[0]

        md = a.list_topics(timeout=10)

        print("Cluster {} metadata (response from broker {}):".format(md.cluster_id, md.orig_broker_name))

        if what in ("all", "brokers"):
            print(" {} brokers:".format(len(md.brokers)))
            for b in iter(md.brokers.values()):
                if b.id == md.controller_id:
                    print("  {}  (controller)".format(b))
                else:
                    print("  {}".format(b))

        if what in ("all", "topics"):
            print(" {} topics:".format(len(md.topics)))
            for t in iter(md.topics.values()):
                if t.error is not None:
                    errstr = ": {}".format(t.error)
                else:
                    errstr = ""

                print("  \"{}\" with {} partition(s){}".format(t, len(t.partitions), errstr))

                for p in iter(t.partitions.values()):
                    if p.error is not None:
                        errstr = ": {}".format(p.error)
                    else:
                        errstr = ""

                    print("partition {} leader: {}, replicas: {},"
                          " isrs: {} errstr: {}".format(p.id, p.leader, p.replicas,
                                                        p.isrs, errstr))

        if what in ("all", "groups"):
            groups = a.list_groups(timeout=10)
            print(" {} consumer groups".format(len(groups)))
            for g in groups:
                if g.error is not None:
                    errstr = ": {}".format(g.error)
                else:
                    errstr = ""

                print(" \"{}\" with {} member(s), protocol: {}, protocol_type: {}{}".format(
                    g, len(g.members), g.protocol, g.protocol_type, errstr))

                for m in g.members:
                    print("id {} client_id: {} client_host: {}".format(m.id, m.client_id, m.client_host))

    def example_list_consumer_groups(a, args):
        """
        List Consumer Groups
        """
        states = {ConsumerGroupState[state] for state in args}
        future = a.list_consumer_groups(request_timeout=10, states=states)
        try:
            list_consumer_groups_result = future.result()
            print("{} consumer groups".format(len(list_consumer_groups_result.valid)))
            for valid in list_consumer_groups_result.valid:
                print("    id: {} is_simple: {} state: {}".format(
                    valid.group_id, valid.is_simple_consumer_group, valid.state))
            print("{} errors".format(len(list_consumer_groups_result.errors)))
            for error in list_consumer_groups_result.errors:
                print("    error: {}".format(error))
        except Exception:
            raise

    def example_describe_consumer_groups(a, args):
        """
        Describe Consumer Groups
        """
        include_auth_ops = bool(int(args[0]))
        args = args[1:]
        futureMap = a.describe_consumer_groups(args, include_authorized_operations=include_auth_ops, request_timeout=10)

        for group_id, future in futureMap.items():
            try:
                g = future.result()
                print("Group Id: {}".format(g.group_id))
                print("  Is Simple          : {}".format(g.is_simple_consumer_group))
                print("  State              : {}".format(g.state))
                print("  Partition Assignor : {}".format(g.partition_assignor))
                print(
                    f"  Coordinator        : {g.coordinator}")
                print("  Members: ")
                for member in g.members:
                    print("    Id                : {}".format(member.member_id))
                    print("    Host              : {}".format(member.host))
                    print("    Client Id         : {}".format(member.client_id))
                    print("    Group Instance Id : {}".format(member.group_instance_id))
                    if member.assignment:
                        print("    Assignments       :")
                        for toppar in member.assignment.topic_partitions:
                            print("      {} [{}]".format(toppar.topic, toppar.partition))
                if (include_auth_ops):
                    print("  Authorized operations: ")
                    op_string = ""
                    for acl_op in g.authorized_operations:
                        op_string += acl_op.name + "  "
                    print("    {}".format(op_string))
            except KafkaException as e:
                print("Error while describing group id '{}': {}".format(group_id, e))
            except Exception:
                raise

    def example_describe_topics(a, args):
        """
        Describe Topics
        """
        include_auth_ops = bool(int(args[0]))
        args = args[1:]
        topics = TopicCollection(topic_names=args)
        futureMap = a.describe_topics(topics, request_timeout=10, include_authorized_operations=include_auth_ops)

        for topic_name, future in futureMap.items():
            try:
                t = future.result()
                print("Topic name             : {}".format(t.name))
                print("Topic id               : {}".format(t.topic_id))
                if (t.is_internal):
                    print("Topic is Internal")

                if (include_auth_ops):
                    print("Authorized operations  : ")
                    op_string = ""
                    for acl_op in t.authorized_operations:
                        op_string += acl_op.name + "  "
                    print("    {}".format(op_string))

                print("Partition Information")
                for partition in t.partitions:
                    print("    Id                : {}".format(partition.id))
                    leader = partition.leader
                    print(f"    Leader            : {leader}")
                    print("    Replicas          : {}".format(len(partition.replicas)))
                    for replica in partition.replicas:
                        print(f"         Replica            : {replica}")
                    print("    In-Sync Replicas  : {}".format(len(partition.isr)))
                    for isr in partition.isr:
                        print(f"         In-Sync Replica    : {isr}")
                    print("")
                print("")

            except KafkaException as e:
                print("Error while describing topic '{}': {}".format(topic_name, e))
            except Exception:
                raise

    def example_describe_cluster(a, args):
        """
        Describe Cluster
        """
        include_auth_ops = bool(int(args[0]))
        args = args[1:]
        future = a.describe_cluster(request_timeout=10, include_authorized_operations=include_auth_ops)
        try:
            c = future.result()
            print("Cluster_id           : {}".format(c.cluster_id))

            if (c.controller):
                print(f"Controller: {c.controller}")
            else:
                print("No Controller Information Available")

            print("Nodes                :")
            for node in c.nodes:
                print(f"  Node: {node}")

            if (include_auth_ops):
                print("Authorized operations: ")
                op_string = ""
                for acl_op in c.authorized_operations:
                    op_string += acl_op.name + "  "
                print("    {}".format(op_string))
        except KafkaException as e:
            print("Error while describing cluster: {}".format(e))
        except Exception:
            raise

    def example_delete_consumer_groups(a, args):
        """
        Delete Consumer Groups
        """
        groups = a.delete_consumer_groups(args, request_timeout=10)
        for group_id, future in groups.items():
            try:
                future.result()  # The result itself is None
                print("Deleted group with id '" + group_id + "' successfully")
            except KafkaException as e:
                print("Error deleting group id '{}': {}".format(group_id, e))
            except Exception:
                raise

    def example_list_consumer_group_offsets(a, args):
        """
        List consumer group offsets
        """

        topic_partitions = []
        for topic, partition in zip(args[1::2], args[2::2]):
            topic_partitions.append(TopicPartition(topic, int(partition)))
        if len(topic_partitions) == 0:
            topic_partitions = None
        groups = [ConsumerGroupTopicPartitions(args[0], topic_partitions)]

        futureMap = a.list_consumer_group_offsets(groups)

        for group_id, future in futureMap.items():
            try:
                response_offset_info = future.result()
                print("Group: " + response_offset_info.group_id)
                for topic_partition in response_offset_info.topic_partitions:
                    if topic_partition.error:
                        print("    Error: " + topic_partition.error.str() + " occurred with " +
                              topic_partition.topic + " [" + str(topic_partition.partition) + "]")
                    else:
                        print("    " + topic_partition.topic +
                              " [" + str(topic_partition.partition) + "]: " + str(topic_partition.offset))

            except KafkaException as e:
                print("Failed to list {}: {}".format(group_id, e))
            except Exception:
                raise

    def example_alter_consumer_group_offsets(a, args):
        """
        Alter consumer group offsets
        """

        topic_partitions = []
        for topic, partition, offset in zip(args[1::3], args[2::3], args[3::3]):
            topic_partitions.append(TopicPartition(topic, int(partition), int(offset)))
        if len(topic_partitions) == 0:
            topic_partitions = None
        groups = [ConsumerGroupTopicPartitions(args[0], topic_partitions)]

        futureMap = a.alter_consumer_group_offsets(groups)

        for group_id, future in futureMap.items():
            try:
                response_offset_info = future.result()
                print("Group: " + response_offset_info.group_id)
                for topic_partition in response_offset_info.topic_partitions:
                    if topic_partition.error:
                        print("    Error: " + topic_partition.error.str() + " occurred with " +
                              topic_partition.topic + " [" + str(topic_partition.partition) + "]")
                    else:
                        print("    " + topic_partition.topic +
                              " [" + str(topic_partition.partition) + "]: " + str(topic_partition.offset))

            except KafkaException as e:
                print("Failed to alter {}: {}".format(group_id, e))
            except Exception:
                raise

    def example_describe_user_scram_credentials(a, args):
        """
        Describe User Scram Credentials
        """
        if len(args) == 0:
            """
            Case: Describes all user scram credentials
            Input: no argument passed or None
            Gets a future which result will give a
            dict[str, UserScramCredentialsDescription]
            or will throw a KafkaException
            """
            f = a.describe_user_scram_credentials()
            try:
                results = f.result()
                for username, response in results.items():
                    print("Username : {}".format(username))
                    for scram_credential_info in response.scram_credential_infos:
                        print(f"    Mechanism: {scram_credential_info.mechanism} " +
                              f"Iterations: {scram_credential_info.iterations}")
            except KafkaException as e:
                print("Failed to describe all user scram credentials : {}".format(e))
            except Exception:
                raise
        else:
            """
            Case: Describe specified user scram credentials
            Input: users is a list
            Gets a dict[str, future] where the result() of
            each future will give a UserScramCredentialsDescription
            or a KafkaException
            """
            futmap = a.describe_user_scram_credentials(args)
            for username, fut in futmap.items():
                print("Username: {}".format(username))
                try:
                    response = fut.result()
                    for scram_credential_info in response.scram_credential_infos:
                        print(f"    Mechanism: {scram_credential_info.mechanism} " +
                              f"Iterations: {scram_credential_info.iterations}")
                except KafkaException as e:
                    print("    Error: {}".format(e))
                except Exception:
                    raise

    def example_alter_user_scram_credentials(a, args):
        """
        AlterUserScramCredentials
        """
        alterations_args = []
        alterations = []
        i = 0
        op_cnt = 0

        while i < len(args):
            op = args[i]
            if op == "UPSERT":
                if i + 5 >= len(args):
                    raise ValueError(
                        f"Invalid number of arguments for alteration {op_cnt}, expected 5, got {len(args) - i - 1}")
                user = args[i + 1]
                mechanism = ScramMechanism[args[i + 2]]
                iterations = int(args[i + 3])
                password = bytes(args[i + 4], 'utf8')
                # if salt is an empty string,
                # set it to None to generate it randomly.
                salt = args[i + 5]
                if not salt:
                    salt = None
                else:
                    salt = bytes(salt, 'utf8')
                alterations_args.append([op, user, mechanism, iterations,
                                         iterations, password, salt])
                i += 6
            elif op == "DELETE":
                if i + 2 >= len(args):
                    raise ValueError(
                        f"Invalid number of arguments for alteration {op_cnt}, expected 2, got {len(args) - i - 1}")
                user = args[i + 1]
                mechanism = ScramMechanism[args[i + 2]]
                alterations_args.append([op, user, mechanism])
                i += 3
            else:
                raise ValueError(f"Invalid alteration {op}, must be UPSERT or DELETE")
            op_cnt += 1

        for alteration_arg in alterations_args:
            op = alteration_arg[0]
            if op == "UPSERT":
                [_, user, mechanism, iterations,
                 iterations, password, salt] = alteration_arg
                scram_credential_info = ScramCredentialInfo(mechanism, iterations)
                upsertion = UserScramCredentialUpsertion(user, scram_credential_info,
                                                         password, salt)
                alterations.append(upsertion)
            elif op == "DELETE":
                [_, user, mechanism] = alteration_arg
                deletion = UserScramCredentialDeletion(user, mechanism)
                alterations.append(deletion)

        futmap = a.alter_user_scram_credentials(alterations)
        for username, fut in futmap.items():
            try:
                fut.result()
                print("{}: Success".format(username))
            except KafkaException as e:
                print("{}: Error: {}".format(username, e))

    def example_list_offsets(a, args):
        topic_partition_offsets = {}
        if len(args) == 0:
            raise ValueError(
                "Invalid number of arguments for list offsets, expected at least 1, got 0")
        i = 1
        partition_i = 1
        isolation_level = IsolationLevel[args[0]]
        while i < len(args):
            if i + 3 > len(args):
                raise ValueError(
                    f"Invalid number of arguments for list offsets, partition {partition_i}, expected 3," +
                    f" got {len(args) - i}")
            topic = args[i]
            partition = int(args[i + 1])
            topic_partition = TopicPartition(topic, partition)

            if "EARLIEST" == args[i + 2]:
                offset_spec = OffsetSpec.earliest()

            elif "LATEST" == args[i + 2]:
                offset_spec = OffsetSpec.latest()

            elif "MAX_TIMESTAMP" == args[i + 2]:
                offset_spec = OffsetSpec.max_timestamp()

            elif "TIMESTAMP" == args[i + 2]:
                if i + 4 > len(args):
                    raise ValueError(
                        f"Invalid number of arguments for list offsets, partition {partition_i}, expected 4" +
                        f", got {len(args) - i}")
                offset_spec = OffsetSpec.for_timestamp(int(args[i + 3]))
                i += 1
            else:
                raise ValueError("Invalid OffsetSpec, must be EARLIEST, LATEST, MAX_TIMESTAMP or TIMESTAMP")
            topic_partition_offsets[topic_partition] = offset_spec
            i = i + 3
            partition_i += 1

        futmap = a.list_offsets(topic_partition_offsets, isolation_level=isolation_level, request_timeout=30)
        for partition, fut in futmap.items():
            try:
                result = fut.result()
                print("Topicname : {} Partition_Index : {} Offset : {} Timestamp : {}"
                      .format(partition.topic, partition.partition, result.offset,
                              result.timestamp))
            except KafkaException as e:
                print("Topicname : {} Partition_Index : {} Error : {}"
                      .format(partition.topic, partition.partition, e))

    if __name__ == '__main__':
        if len(sys.argv) < 3:
            sys.stderr.write('Usage: %s <bootstrap-brokers> <operation> <args..>\n\n' % sys.argv[0])
            sys.stderr.write('operations:\n')
            sys.stderr.write(' create_topics <topic1> <topic2> ..\n')
            sys.stderr.write(' delete_topics <topic1> <topic2> ..\n')
            sys.stderr.write(' create_partitions <topic1> <new_total_count1> <topic2> <new_total_count2> ..\n')
            sys.stderr.write(' describe_configs <resource_type1> <resource_name1> <resource2> <resource_name2> ..\n')
            sys.stderr.write(' alter_configs <resource_type1> <resource_name1> ' +
                             '<config=val,config2=val2> <resource_type2> <resource_name2> <config..> ..\n')
            sys.stderr.write(' incremental_alter_configs <resource_type1> <resource_name1> ' +
                             '<config1=op1:val1;config2=op2:val2;config3=DELETE> ' +
                             '<resource_type2> <resource_name2> <config1=op1:..> ..\n')
            sys.stderr.write(' delta_alter_configs <resource_type1> <resource_name1> ' +
                             '<config=val,config2=val2> <resource_type2> <resource_name2> <config..> ..\n')
            sys.stderr.write(' create_acls <resource_type1> <resource_name1> <resource_patter_type1> ' +
                             '<principal1> <host1> <operation1> <permission_type1> ..\n')
            sys.stderr.write(' describe_acls <resource_type1 <resource_name1> <resource_patter_type1> ' +
                             '<principal1> <host1> <operation1> <permission_type1> ..\n')
            sys.stderr.write(' delete_acls <resource_type1> <resource_name1> <resource_patter_type1> ' +
                             '<principal1> <host1> <operation1> <permission_type1> ..\n')
            sys.stderr.write(' list [<all|topics|brokers|groups>]\n')
            sys.stderr.write(' list_consumer_groups [<state1> <state2> ..]\n')
            sys.stderr.write(' describe_consumer_groups <include_authorized_operations> <group1> <group2> ..\n')
            sys.stderr.write(' describe_topics <include_authorized_operations> <topic1> <topic2> ..\n')
            sys.stderr.write(' describe_cluster <include_authorized_operations>\n')
            sys.stderr.write(' delete_consumer_groups <group1> <group2> ..\n')
            sys.stderr.write(' list_consumer_group_offsets <group> [<topic1> <partition1> <topic2> <partition2> ..]\n')
            sys.stderr.write(
                ' alter_consumer_group_offsets <group> <topic1> <partition1> <offset1> ' +
                '<topic2> <partition2> <offset2> ..\n')
            sys.stderr.write(' describe_user_scram_credentials [<user1> <user2> ..]\n')
            sys.stderr.write(' alter_user_scram_credentials UPSERT <user1> <mechanism1> ' +
                             '<iterations1> <password1> <salt1> ' +
                             '[UPSERT <user2> <mechanism2> <iterations2> ' +
                             ' <password2> <salt2> DELETE <user3> <mechanism3> ..]\n')
            sys.stderr.write(' list_offsets <isolation_level> <topic1> <partition1> <offset_spec1> ' +
                             '[<topic2> <partition2> <offset_spec2> ..]\n')

            sys.exit(1)

        broker = sys.argv[1]
        operation = sys.argv[2]
        args = sys.argv[3:]

        # Create Admin client
        a = AdminClient({'bootstrap.servers': broker})

        opsmap = {'create_topics': example_create_topics,
                  'delete_topics': example_delete_topics,
                  'create_partitions': example_create_partitions,
                  'describe_configs': example_describe_configs,
                  'alter_configs': example_alter_configs,
                  'incremental_alter_configs': example_incremental_alter_configs,
                  'delta_alter_configs': example_delta_alter_configs,
                  'create_acls': example_create_acls,
                  'describe_acls': example_describe_acls,
                  'delete_acls': example_delete_acls,
                  'list': example_list,
                  'list_consumer_groups': example_list_consumer_groups,
                  'describe_consumer_groups': example_describe_consumer_groups,
                  'describe_topics': example_describe_topics,
                  'describe_cluster': example_describe_cluster,
                  'delete_consumer_groups': example_delete_consumer_groups,
                  'list_consumer_group_offsets': example_list_consumer_group_offsets,
                  'alter_consumer_group_offsets': example_alter_consumer_group_offsets,
                  'describe_user_scram_credentials': example_describe_user_scram_credentials,
                  'alter_user_scram_credentials': example_alter_user_scram_credentials,
                  'list_offsets': example_list_offsets}

        if operation not in opsmap:
            sys.stderr.write('Unknown operation: %s\n' % operation)
            sys.exit(1)

        opsmap[operation](a, args)

class AIOProducer:
    def __init__(self, configs, loop=None):
        self._loop = loop or asyncio.get_event_loop()
        self._producer = confluent_kafka.Producer(configs)
        self._cancelled = False
        self._poll_thread = Thread(target=self._poll_loop)
        self._poll_thread.start()

    def _poll_loop(self):
        while not self._cancelled:
            self._producer.poll(0.1)

    def close(self):
        self._cancelled = True
        self._poll_thread.join()

    def produce(self, topic, value):
        """
        An awaitable produce method.
        """
        result = self._loop.create_future()

        def ack(err, msg):
            if err:
                self._loop.call_soon_threadsafe(result.set_exception, KafkaException(err))
            else:
                self._loop.call_soon_threadsafe(result.set_result, msg)
        self._producer.produce(topic, value, on_delivery=ack)
        return result

    def produce2(self, topic, value, on_delivery):
        """
        A produce method in which delivery notifications are made available
        via both the returned future and on_delivery callback (if specified).
        """
        result = self._loop.create_future()

        def ack(err, msg):
            if err:
                self._loop.call_soon_threadsafe(
                    result.set_exception, KafkaException(err))
            else:
                self._loop.call_soon_threadsafe(
                    result.set_result, msg)
            if on_delivery:
                self._loop.call_soon_threadsafe(
                    on_delivery, err, msg)
        self._producer.produce(topic, value, on_delivery=ack)
        return result


class Producer:
    def __init__(self, configs):
        self._producer = confluent_kafka.Producer(configs)
        self._cancelled = False
        self._poll_thread = Thread(target=self._poll_loop)
        self._poll_thread.start()

    def _poll_loop(self):
        while not self._cancelled:
            self._producer.poll(0.1)

    def close(self):
        self._cancelled = True
        self._poll_thread.join()

    def produce(self, topic, value, on_delivery=None):
        self._producer.produce(topic, value, on_delivery=on_delivery)


config = {"bootstrap.servers": "localhost:9092"}

app = FastAPI()


class Item(BaseModel):
    name: str


aio_producer = None
producer = None


@app.on_event("startup")
async def startup_event():
    global producer, aio_producer
    aio_producer = AIOProducer(config)
    producer = Producer(config)


@app.on_event("shutdown")
def shutdown_event():
    aio_producer.close()
    producer.close()


@app.post("/items1")
async def create_item1(item: Item):
    try:
        result = await aio_producer.produce("items", item.name)
        return {"timestamp": result.timestamp()}
    except KafkaException as ex:
        raise HTTPException(status_code=500, detail=ex.args[0].str())

cnt = 0


def ack(err, msg):
    global cnt
    cnt = cnt + 1


@app.post("/items2")
async def create_item2(item: Item):
    try:
        aio_producer.produce2("items", item.name, on_delivery=ack)
        return {"timestamp": time()}
    except KafkaException as ex:
        raise HTTPException(status_code=500, detail=ex.args[0].str())


@app.post("/items3")
async def create_item3(item: Item):
    try:
        producer.produce("items", item.name, on_delivery=ack)
        return {"timestamp": time()}
    except KafkaException as ex:
        raise HTTPException(status_code=500, detail=ex.args[0].str())


@app.post("/items4")
async def create_item4(item: Item):
    try:
        producer.produce("items", item.name)
        return {"timestamp": time()}
    except KafkaException as ex:
        raise HTTPException(status_code=500, detail=ex.args[0].str())


@app.post("/items5")
async def create_item5(item: Item):
    return {"timestamp": time()}



class User(object):
    """
    User record

    Args:
        name (str): User's name

        favorite_number (int): User's favorite number

        favorite_color (str): User's favorite color
    """

    def __init__(self, name=None, favorite_number=None, favorite_color=None):
        self.name = name
        self.favorite_number = favorite_number
        self.favorite_color = favorite_color


def dict_to_user(obj, ctx):
    """
    Converts object literal(dict) to a User instance.

    Args:
        obj (dict): Object literal(dict)

        ctx (SerializationContext): Metadata pertaining to the serialization
            operation.
    """

    if obj is None:
        return None

    return User(name=obj['name'],
                favorite_number=obj['favorite_number'],
                favorite_color=obj['favorite_color'])


def main(args):
    topic = args.topic
    is_specific = args.specific == "true"

    if is_specific:
        schema = "user_specific.avsc"
    else:
        schema = "user_generic.avsc"

    path = os.path.realpath(os.path.dirname(__file__))
    with open(f"{path}/avro/{schema}") as f:
        schema_str = f.read()

    sr_conf = {'url': args.schema_registry}
    schema_registry_client = SchemaRegistryClient(sr_conf)

    avro_deserializer = AvroDeserializer(schema_registry_client,
                                         schema_str,
                                         dict_to_user)

    consumer_conf = {'bootstrap.servers': args.bootstrap_servers,
                     'group.id': args.group,
                     'auto.offset.reset': "earliest"}

    consumer = Consumer(consumer_conf)
    consumer.subscribe([topic])

    while True:
        try:
            # SIGINT can't be handled when polling, limit timeout to 1 second.
            msg = consumer.poll(1.0)
            if msg is None:
                continue

            user = avro_deserializer(msg.value(), SerializationContext(msg.topic(), MessageField.VALUE))
            if user is not None:
                print("User record {}: name: {}\n"
                      "\tfavorite_number: {}\n"
                      "\tfavorite_color: {}\n"
                      .format(msg.key(), user.name,
                              user.favorite_number,
                              user.favorite_color))
        except KeyboardInterrupt:
            break

    consumer.close()



class User(object):
    """
    User record

    Args:
        name (str): User's name

        favorite_number (int): User's favorite number

        favorite_color (str): User's favorite color

        address(str): User's address; confidential
    """

    def __init__(self, name, address, favorite_number, favorite_color):
        self.name = name
        self.favorite_number = favorite_number
        self.favorite_color = favorite_color
        # address should not be serialized, see user_to_dict()
        self._address = address


def user_to_dict(user, ctx):
    """
    Returns a dict representation of a User instance for serialization.

    Args:
        user (User): User instance.

        ctx (SerializationContext): Metadata pertaining to the serialization
            operation.

    Returns:
        dict: Dict populated with user attributes to be serialized.
    """

    # User._address must not be serialized; omit from dict
    return dict(name=user.name,
                favorite_number=user.favorite_number,
                favorite_color=user.favorite_color)


def delivery_report(err, msg):
    """
    Reports the failure or success of a message delivery.

    Args:
        err (KafkaError): The error that occurred on None on success.

        msg (Message): The message that was produced or failed.

    Note:
        In the delivery report callback the Message.key() and Message.value()
        will be the binary format as encoded by any configured Serializers and
        not the same object that was passed to produce().
        If you wish to pass the original object(s) for key and value to delivery
        report callback we recommend a bound callback or lambda where you pass
        the objects along.
    """

    if err is not None:
        print("Delivery failed for User record {}: {}".format(msg.key(), err))
        return
    print('User record {} successfully produced to {} [{}] at offset {}'.format(
        msg.key(), msg.topic(), msg.partition(), msg.offset()))


def main(args):
    topic = args.topic
    is_specific = args.specific == "true"

    if is_specific:
        schema = "user_specific.avsc"
    else:
        schema = "user_generic.avsc"

    path = os.path.realpath(os.path.dirname(__file__))
    with open(f"{path}/avro/{schema}") as f:
        schema_str = f.read()

    schema_registry_conf = {'url': args.schema_registry}
    schema_registry_client = SchemaRegistryClient(schema_registry_conf)

    avro_serializer = AvroSerializer(schema_registry_client,
                                     schema_str,
                                     user_to_dict)

    string_serializer = StringSerializer('utf_8')

    producer_conf = {'bootstrap.servers': args.bootstrap_servers}

    producer = Producer(producer_conf)

    print("Producing user records to topic {}. ^C to exit.".format(topic))
    while True:
        # Serve on_delivery callbacks from previous calls to produce()
        producer.poll(0.0)
        try:
            user_name = input("Enter name: ")
            user_address = input("Enter address: ")
            user_favorite_number = int(input("Enter favorite number: "))
            user_favorite_color = input("Enter favorite color: ")
            user = User(name=user_name,
                        address=user_address,
                        favorite_color=user_favorite_color,
                        favorite_number=user_favorite_number)
            producer.produce(topic=topic,
                             key=string_serializer(str(uuid4())),
                             value=avro_serializer(user, SerializationContext(topic, MessageField.VALUE)),
                             on_delivery=delivery_report)
        except KeyboardInterrupt:
            break
        except ValueError:
            print("Invalid input, discarding record...")
            continue

    print("\nFlushing records...")
    producer.flush()

def process_input(msg):
    """
    Base64 encodes msg key/value contents
    :param msg:
    :returns: transformed key, value
    :rtype: tuple
    """

    key, value = None, None
    if msg.key() is not None:
        key = b64encode(msg.key())
    if msg.value() is not None:
        value = b64encode(msg.value())

    return key, value


def delivery_report(err, msg):
    """
    Reports message delivery status; success or failure
    :param KafkaError err: reason for delivery failure
    :param Message msg:
    :returns: None
    """
    if err:
        print('Message delivery failed ({} [{}]): {}'.format(
            msg.topic(), str(msg.partition()), err))


def main(args):
    brokers = args.brokers
    group_id = args.group_id
    input_topic = args.input_topic
    input_partition = args.input_partition
    output_topic = args.output_topic

    consumer = Consumer({
        'bootstrap.servers': brokers,
        'group.id': group_id,
        'auto.offset.reset': 'earliest',
        # Do not advance committed offsets outside of the transaction.
        # Consumer offsets are committed along with the transaction
        # using the producer's send_offsets_to_transaction() API.
        'enable.auto.commit': False,
        'enable.partition.eof': True,
    })

    # Prior to KIP-447 being supported each input partition requires
    # its own transactional producer, so in this example we use
    # assign() to a single partition rather than subscribe().
    # A more complex alternative is to dynamically create a producer per
    # partition in subscribe's rebalance callback.
    consumer.assign([TopicPartition(input_topic, input_partition)])

    producer = Producer({
        'bootstrap.servers': brokers,
        'transactional.id': 'eos-transactions.py'
    })

    # Initialize producer transaction.
    producer.init_transactions()
    # Start producer transaction.
    producer.begin_transaction()

    eof = {}
    msg_cnt = 0
    print("=== Starting Consume-Transform-Process loop ===")
    while True:
        # serve delivery reports from previous produce()s
        producer.poll(0)

        # read message from input_topic
        msg = consumer.poll(timeout=1.0)
        if msg is None:
            continue

        topic, partition = msg.topic(), msg.partition()
        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                eof[(topic, partition)] = True
                print("=== Reached the end of {} [{}] at {}====".format(
                    topic, partition, msg.offset()))

                if len(eof) == len(consumer.assignment()):
                    print("=== Reached end of input ===")
                    break
            continue
        # clear EOF if a new message has been received
        eof.pop((topic, partition), None)

        msg_cnt += 1

        # process message
        processed_key, processed_value = process_input(msg)

        # produce transformed message to output topic
        producer.produce(output_topic, processed_value, processed_key,
                         on_delivery=delivery_report)

        if msg_cnt % 100 == 0:
            print("=== Committing transaction with {} messages at input offset {} ===".format(
                msg_cnt, msg.offset()))
            # Send the consumer's position to transaction to commit
            # them along with the transaction, committing both
            # input and outputs in the same transaction is what provides EOS.
            producer.send_offsets_to_transaction(
                consumer.position(consumer.assignment()),
                consumer.consumer_group_metadata())

            # Commit the transaction
            producer.commit_transaction()

            # Begin new transaction
            producer.begin_transaction()
            msg_cnt = 0

    print("=== Committing final transaction with {} messages ===".format(msg_cnt))
    # commit processed message offsets to the transaction
    producer.send_offsets_to_transaction(
        consumer.position(consumer.assignment()),
        consumer.consumer_group_metadata())

    # commit transaction
    producer.commit_transaction()

    consumer.close()


def user_to_dict(user, ctx):
    """
    Returns a dict representation of a User instance for serialization.

    Args:
        user (User): User instance.

        ctx (SerializationContext): Metadata pertaining to the serialization
            operation.

    Returns:
        dict: Dict populated with user attributes to be serialized.
    """

    # User._address must not be serialized; omit from dict
    return dict(name=user.name,
                favorite_number=user.favorite_number,
                favorite_color=user.favorite_color)


def delivery_report(err, msg):
    """
    Reports the success or failure of a message delivery.

    Args:
        err (KafkaError): The error that occurred on None on success.
        msg (Message): The message that was produced or failed.
    """

    if err is not None:
        print("Delivery failed for User record {}: {}".format(msg.key(), err))
        return
    print('User record {} successfully produced to {} [{}] at offset {}'.format(
        msg.key(), msg.topic(), msg.partition(), msg.offset()))


def main(args):
    topic = args.topic

    schema_str = """
    {
      "$schema": "http://json-schema.org/draft-07/schema#",
      "title": "User",
      "description": "A Confluent Kafka Python User",
      "type": "object",
      "properties": {
        "name": {
          "description": "User's name",
          "type": "string"
        },
        "favorite_number": {
          "description": "User's favorite number",
          "type": "number",
          "exclusiveMinimum": 0
        },
        "favorite_color": {
          "description": "User's favorite color",
          "type": "string"
        }
      },
      "required": [ "name", "favorite_number", "favorite_color" ]
    }
    """
    schema_registry_conf = {'url': args.schema_registry}
    schema_registry_client = SchemaRegistryClient(schema_registry_conf)

    string_serializer = StringSerializer('utf_8')
    json_serializer = JSONSerializer(schema_str, schema_registry_client, user_to_dict)

    producer = Producer({'bootstrap.servers': args.bootstrap_servers})

    print("Producing user records to topic {}. ^C to exit.".format(topic))
    while True:
        # Serve on_delivery callbacks from previous calls to produce()
        producer.poll(0.0)
        try:
            user_name = input("Enter name: ")
            user_address = input("Enter address: ")
            user_favorite_number = int(input("Enter favorite number: "))
            user_favorite_color = input("Enter favorite color: ")
            user = User(name=user_name,
                        address=user_address,
                        favorite_color=user_favorite_color,
                        favorite_number=user_favorite_number)
            producer.produce(topic=topic,
                             key=string_serializer(str(uuid4())),
                             value=json_serializer(user, SerializationContext(topic, MessageField.VALUE)),
                             on_delivery=delivery_report)
        except KeyboardInterrupt:
            break
        except ValueError:
            print("Invalid input, discarding record...")
            continue

    print("\nFlushing records...")
    producer.flush()
def main(args):
    topic = args.topic
    delimiter = args.delimiter
    producer_conf = producer_config(args)
    producer = Producer(producer_conf)
    serializer = StringSerializer('utf_8')

    print('Producing records to topic {}. ^C to exit.'.format(topic))
    while True:
        # Serve on_delivery callbacks from previous calls to produce()
        producer.poll(0.0)
        try:
            msg_data = input(">")
            msg = msg_data.split(delimiter)
            if len(msg) == 2:
                producer.produce(topic=topic,
                                 key=serializer(msg[0]),
                                 value=serializer(msg[1]),
                                 on_delivery=delivery_report)
            else:
                producer.produce(topic=topic,
                                 value=serializer(msg[0]),
                                 on_delivery=delivery_report)
        except KeyboardInterrupt:
            break

    print('\nFlushing {} records...'.format(len(producer)))
    producer.flush()

def delivery_report(err, msg):
    """
    Reports the failure or success of a message delivery.

    Args:
        err (KafkaError): The error that occurred on None on success.
        msg (Message): The message that was produced or failed.
    """

    if err is not None:
        print("Delivery failed for User record {}: {}".format(msg.key(), err))
        return
    print('User record {} successfully produced to {} [{}] at offset {}'.format(
        msg.key(), msg.topic(), msg.partition(), msg.offset()))


def main(args):
    topic = args.topic

    schema_registry_conf = {'url': args.schema_registry}
    schema_registry_client = SchemaRegistryClient(schema_registry_conf)

    string_serializer = StringSerializer('utf8')
    protobuf_serializer = ProtobufSerializer(user_pb2.User,
                                             schema_registry_client,
                                             {'use.deprecated.format': False})

    producer_conf = {'bootstrap.servers': args.bootstrap_servers}

    producer = Producer(producer_conf)

    print("Producing user records to topic {}. ^C to exit.".format(topic))
    while True:
        # Serve on_delivery callbacks from previous calls to produce()
        producer.poll(0.0)
        try:
            user_name = input("Enter name: ")
            user_favorite_number = int(input("Enter favorite number: "))
            user_favorite_color = input("Enter favorite color: ")
            user = user_pb2.User(name=user_name,
                                 favorite_color=user_favorite_color,
                                 favorite_number=user_favorite_number)
            producer.produce(topic=topic, partition=0,
                             key=string_serializer(str(uuid4())),
                             value=protobuf_serializer(user, SerializationContext(topic, MessageField.VALUE)),
                             on_delivery=delivery_report)
        except (KeyboardInterrupt, EOFError):
            break
        except ValueError:
            print("Invalid input, discarding record...")
            continue

    print("\nFlushing records...")
    producer.flush()

def sasl_conf(args):
    sasl_mechanism = args.sasl_mechanism.upper()

    sasl_conf = {'sasl.mechanism': sasl_mechanism,
                 # Set to SASL_SSL to enable TLS support.
                 'security.protocol': 'SASL_PLAINTEXT'}

    if sasl_mechanism != 'GSSAPI':
        sasl_conf.update({'sasl.username': args.user_principal,
                          'sasl.password': args.user_secret})

    if sasl_mechanism == 'GSSAPI':
        sasl_conf.update({'sasl.kerberos.service.name', args.broker_principal,
                          # Keytabs are not supported on Windows. Instead the
                          # the logged on user's credentials are used to
                          # authenticate.
                          'sasl.kerberos.principal', args.user_principal,
                          'sasl.kerberos.keytab', args.user_secret})
    return sasl_conf

def test_error_cb():
    """ Test the error callback. """

    global seen_all_brokers_down

    # Configure an invalid broker and make sure the ALL_BROKERS_DOWN
    # error is seen in the error callback.
    p = Producer({'bootstrap.servers': '127.0.0.1:1', 'socket.timeout.ms': 10,
                  'error_cb': error_cb})

    t_end = time.time() + 5

    while not seen_all_brokers_down and time.time() < t_end:
        p.poll(1)

    assert seen_all_brokers_down


def test_fatal():
    """ Test fatal exceptions """

    # Configure an invalid broker and make sure the ALL_BROKERS_DOWN
    # error is seen in the error callback.
    p = Producer({'error_cb': error_cb})

    with pytest.raises(KafkaException) as exc:
        raise KafkaException(KafkaError(KafkaError.MEMBER_ID_REQUIRED,
                                        fatal=True))
    err = exc.value.args[0]
    assert isinstance(err, KafkaError)
    assert err.fatal()
    assert not err.retriable()
    assert not err.txn_requires_abort()

    p.poll(0)  # Need some p use to avoid flake8 unused warning


def test_retriable():
    """ Test retriable exceptions """

    with pytest.raises(KafkaException) as exc:
        raise KafkaException(KafkaError(KafkaError.MEMBER_ID_REQUIRED,
                                        retriable=True))
    err = exc.value.args[0]
    assert isinstance(err, KafkaError)
    assert not err.fatal()
    assert err.retriable()
    assert not err.txn_requires_abort()


def test_abortable():
    """ Test abortable exceptions """

    with pytest.raises(KafkaException) as exc:
        raise KafkaException(KafkaError(KafkaError.MEMBER_ID_REQUIRED,
                                        txn_requires_abort=True))
    err = exc.value.args[0]
    assert isinstance(err, KafkaError)
    assert not err.fatal()
    assert not err.retriable()
    assert err.txn_requires_abort()


def test_subclassing():
    class MyExc(KafkaException):
        def a_method(self):
            return "yes"
    err = MyExc()
    assert err.a_method() == "yes"
    assert isinstance(err, KafkaException)


def test_kafkaError_custom_msg():
    err = KafkaError(KafkaError._ALL_BROKERS_DOWN, "Mayday!")
    assert err == KafkaError._ALL_BROKERS_DOWN
    assert err.str() == "Mayday!"
    assert not err.fatal()
    assert not err.fatal()
    assert not err.retriable()
    assert not err.txn_requires_abort()


def test_kafkaError_unknonw_error():
    with pytest.raises(KafkaException, match="Err-12345?") as e:
        raise KafkaError(12345)
    assert not e.value.args[0].fatal()
    assert not e.value.args[0].retriable()
    assert not e.value.args[0].txn_requires_abort()


def test_kafkaException_unknown_KafkaError_with_subclass():
    class MyException(KafkaException):
        def __init__(self, error_code):
            super(MyException, self).__init__(KafkaError(error_code))

    with pytest.raises(KafkaException, match="Err-12345?") as e:
        raise MyException(12345)
    assert not e.value.args[0].fatal()
    assert not e.value.args[0].fatal()
    assert not e.value.args[0].retriable()
    assert not e.value.args[0].txn_requires_abort()


def test_basic_api():
    """ Basic API tests, these wont really do anything since there is no
        broker configured. """

    with pytest.raises(TypeError) as ex:
        p = Producer()
    assert ex.match('expected configuration dict')

    p = Producer({'socket.timeout.ms': 10,
                  'error_cb': error_cb,
                  'message.timeout.ms': 10})

    p.produce('mytopic')
    p.produce('mytopic', value='somedata', key='a key')

    def on_delivery(err, msg):
        print('delivery', err, msg)
        # Since there is no broker, produced messages should time out.
        assert err.code() == KafkaError._MSG_TIMED_OUT
        print('message latency', msg.latency())

    p.produce(topic='another_topic', value='testing', partition=9,
              callback=on_delivery)

    p.poll(0.001)

    p.flush(0.002)
    p.flush()

    try:
        p.list_topics(timeout=0.2)
    except KafkaException as e:
        assert e.args[0].code() in (KafkaError._TIMED_OUT, KafkaError._TRANSPORT)


def test_produce_timestamp():
    """ Test produce() with timestamp arg """
    p = Producer({'socket.timeout.ms': 10,
                  'error_cb': error_cb,
                  'message.timeout.ms': 10})

    # Requires librdkafka >=v0.9.4

    try:
        p.produce('mytopic', timestamp=1234567)
    except NotImplementedError:
        # Should only fail on non-supporting librdkafka
        if libversion()[1] >= 0x00090400:
            raise

    p.flush()


# Should be updated to 0.11.4 when it is released
@pytest.mark.skipif(libversion()[1] < 0x000b0400,
                    reason="requires librdkafka >=0.11.4")
def test_produce_headers():
    """ Test produce() with timestamp arg """
    p = Producer({'socket.timeout.ms': 10,
                  'error_cb': error_cb,
                  'message.timeout.ms': 10})

    binval = pack('hhl', 1, 2, 3)

    headers_to_test = [
        [('headerkey', 'headervalue')],
        [('dupkey', 'dupvalue'), ('empty', ''), ('dupkey', 'dupvalue')],
        [('dupkey', 'dupvalue'), ('dupkey', 'diffvalue')],
        [('key_with_null_value', None)],
        [('binaryval', binval)],
        [('alreadyutf8', u'Småland'.encode('utf-8'))],
        [('isunicode', 'Jämtland')],

        {'headerkey': 'headervalue'},
        {'dupkey': 'dupvalue', 'empty': '', 'dupkey': 'dupvalue'},  # noqa: F601
        {'dupkey': 'dupvalue', 'dupkey': 'diffvalue'},  # noqa: F601
        {'key_with_null_value': None},
        {'binaryval': binval},
        {'alreadyutf8': u'Småland'.encode('utf-8')},
        {'isunicode': 'Jämtland'}
        ]

    for headers in headers_to_test:
        print('headers', type(headers), headers)
        p.produce('mytopic', value='somedata', key='a key', headers=headers)
        p.produce('mytopic', value='somedata', headers=headers)

    with pytest.raises(TypeError):
        p.produce('mytopic', value='somedata', key='a key', headers=('a', 'b'))

    with pytest.raises(TypeError):
        p.produce('mytopic', value='somedata', key='a key', headers=[('malformed_header')])

    with pytest.raises(TypeError):
        p.produce('mytopic', value='somedata', headers={'anint': 1234})

    p.flush()


# Should be updated to 0.11.4 when it is released
@pytest.mark.skipif(libversion()[1] >= 0x000b0400,
                    reason="Old versions should fail when using headers")
def test_produce_headers_should_fail():
    """ Test produce() with timestamp arg """
    p = Producer({'socket.timeout.ms': 10,
                  'error_cb': error_cb,
                  'message.timeout.ms': 10})

    with pytest.raises(NotImplementedError) as ex:
        p.produce('mytopic', value='somedata', key='a key', headers=[('headerkey', 'headervalue')])
    assert ex.match('Producer message headers requires confluent-kafka-python built for librdkafka version >=v0.11.4')


def test_subclassing():
    class SubProducer(Producer):
        def __init__(self, conf, topic):
            super(SubProducer, self).__init__(conf)
            self.topic = topic

        def produce_hi(self):
            super(SubProducer, self).produce(self.topic, value='hi')

    sp = SubProducer(dict(), 'atopic')
    assert isinstance(sp, SubProducer)

    # Invalid config should fail
    with pytest.raises(KafkaException):
        sp = SubProducer({'should.fail': False}, 'mytopic')

    sp = SubProducer({'log.thread.name': True}, 'mytopic')
    sp.produce('someother', value='not hello')
    sp.produce_hi()


def test_dr_msg_errstr():
    """
    Test that the error string for failed messages works (issue #129).
    The underlying problem is that librdkafka reuses the message payload
    for error value on Consumer messages, but on Producer messages the
    payload is the original payload and no rich error string exists.
    """
    p = Producer({"message.timeout.ms": 10})

    def handle_dr(err, msg):
        # Neither message payloads must not affect the error string.
        assert err is not None
        assert err.code() == KafkaError._MSG_TIMED_OUT
        assert "Message timed out" in err.str()

    # Unicode safe string
    p.produce('mytopic', "This is the message payload", on_delivery=handle_dr)

    # Invalid unicode sequence
    p.produce('mytopic', "\xc2\xc2", on_delivery=handle_dr)

    p.flush()


def test_set_partitioner_murmur2():
    """
    Test ability to set built-in partitioner type murmur
    """
    Producer({'partitioner': 'murmur2'})


def test_set_partitioner_murmur2_random():
    """
    Test ability to set built-in partitioner type murmur2_random
    """
    Producer({'partitioner': 'murmur2_random'})


def test_set_invalid_partitioner_murmur():
    """
    Assert invalid partitioner raises KafkaException
    """
    with pytest.raises(KafkaException) as ex:
        Producer({'partitioner': 'murmur'})
    assert ex.match('Invalid value for configuration property "partitioner": murmur')


def test_transaction_api():
    """ Excercise the transactional API """
    p = Producer({"transactional.id": "test"})

    with pytest.raises(KafkaException) as ex:
        p.init_transactions(0.5)
    assert ex.value.args[0].code() == KafkaError._TIMED_OUT
    assert ex.value.args[0].retriable() is True
    assert ex.value.args[0].fatal() is False
    assert ex.value.args[0].txn_requires_abort() is False

    # Any subsequent APIs will fail since init did not succeed.
    with pytest.raises(KafkaException) as ex:
        p.begin_transaction()
    assert ex.value.args[0].code() == KafkaError._CONFLICT
    assert ex.value.args[0].retriable() is True
    assert ex.value.args[0].fatal() is False
    assert ex.value.args[0].txn_requires_abort() is False

    consumer = Consumer({"group.id": "testgroup"})
    group_metadata = consumer.consumer_group_metadata()
    consumer.close()

    with pytest.raises(KafkaException) as ex:
        p.send_offsets_to_transaction([TopicPartition("topic", 0, 123)],
                                      group_metadata)
    assert ex.value.args[0].code() == KafkaError._CONFLICT
    assert ex.value.args[0].retriable() is True
    assert ex.value.args[0].fatal() is False
    assert ex.value.args[0].txn_requires_abort() is False

    with pytest.raises(KafkaException) as ex:
        p.commit_transaction(0.5)
    assert ex.value.args[0].code() == KafkaError._CONFLICT
    assert ex.value.args[0].retriable() is True
    assert ex.value.args[0].fatal() is False
    assert ex.value.args[0].txn_requires_abort() is False

    with pytest.raises(KafkaException) as ex:
        p.abort_transaction(0.5)
    assert ex.value.args[0].code() == KafkaError._CONFLICT
    assert ex.value.args[0].retriable() is True
    assert ex.value.args[0].fatal() is False
    assert ex.value.args[0].txn_requires_abort() is False


def test_purge():
    """
    Verify that when we have a higher message.timeout.ms timeout, we can use purge()
    to stop waiting for messages and get delivery reports
    """
    p = Producer(
        {"socket.timeout.ms": 10, "error_cb": error_cb, "message.timeout.ms": 30000}
    )  # 30 seconds

    # Hack to detect on_delivery was called because inner functions can modify nonlocal objects.
    # When python2 support is dropped, we can use the "nonlocal" keyword instead
    cb_detector = {"on_delivery_called": False}

    def on_delivery(err, msg):
        cb_detector["on_delivery_called"] = True
        # Because we are purging messages, we should see a PURGE_QUEUE kafka error
        assert err.code() == KafkaError._PURGE_QUEUE

    # Our message won't be delivered, but also won't timeout yet because our timeout is 30s.
    p.produce(topic="some_topic", value="testing", partition=9, callback=on_delivery)
    p.flush(0.002)
    assert not cb_detector["on_delivery_called"]

    # When in_queue set to false, we won't purge the message and get delivery callback
    p.purge(in_queue=False)
    p.flush(0.002)
    assert not cb_detector["on_delivery_called"]

    # When we purge including the queue, the message should have delivered a delivery report
    # with a PURGE_QUEUE error
    p.purge()
    p.flush(0.002)
    assert cb_detector["on_delivery_called"]


def test_producer_bool_value():
    """
    Make sure producer has a truth-y bool value
    See https://github.com/confluentinc/confluent-kafka-python/issues/1427
    """

    p = Producer({})
    assert bool(p)

def test_sort():
    """ TopicPartition sorting (rich comparator) """

    # sorting uses the comparator
    correct = [TopicPartition('topic1', 3),
               TopicPartition('topic3', 0),
               TopicPartition('topicA', 5),
               TopicPartition('topicA', 5)]

    tps = sorted([TopicPartition('topicA', 5),
                  TopicPartition('topic3', 0),
                  TopicPartition('topicA', 5),
                  TopicPartition('topic1', 3)])

    assert correct == tps


def test_cmp():
    """ TopicPartition comparator """

    assert TopicPartition('aa', 19002) > TopicPartition('aa', 0)
    assert TopicPartition('aa', 13) >= TopicPartition('aa', 12)
    assert TopicPartition('BaB', 9) != TopicPartition('Card', 9)
    assert TopicPartition('b3x', 4) == TopicPartition('b3x', 4)
    assert TopicPartition('ulv', 2) < TopicPartition('xy', 0)
    assert TopicPartition('ulv', 2) <= TopicPartition('ulv', 3)


def test_hash():

    tp1 = TopicPartition('test', 99)
    tp2 = TopicPartition('somethingelse', 12)
    assert hash(tp1) != hash(tp2)


def test_subclassing():
    class SubTopicPartition(TopicPartition):
        def __init__(self, topic_part_str):
            topic, part = topic_part_str.split(":")
            super(SubTopicPartition, self).__init__(topic=topic, partition=int(part))

    st = SubTopicPartition("topic1:0")
    assert st.topic == "topic1"
    assert st.partition == 0

    st = SubTopicPartition("topic2:920")
    assert st.topic == "topic2"
    assert st.partition == 920


def build_doctree(tree, prefix, parent):
    """ Build doctree dict with format:
          dict key = full class/type name (e.g, "confluent_kafka.Message.timestamp")
          value = object
    """
    for n in dir(parent):
        if n.startswith('__') or n == 'cimpl':
            # Skip internals and the C module (it is automatically imported
            # to other names in __init__.py)
            continue

        o = parent.__dict__.get(n)
        if o is None:
            # Skip inherited (not overloaded)
            continue

        if isinstance(o, ModuleType):
            # Skip imported modules
            continue

        full = prefix + n
        tree[full].append(o)

        if hasattr(o, '__dict__'):
            is_module = isinstance(o, ModuleType)
            is_ck_package = o.__dict__.get('__module__', '').startswith('confluent_kafka.')
            is_cimpl_package = o.__dict__.get('__module__', '').startswith('cimpl.')
            if not is_module or is_ck_package or is_cimpl_package:
                build_doctree(tree, full + '.', o)


def test_verify_docs():
    """ Make sure all exported functions, classes, etc, have proper docstrings
    """

    tree = defaultdict(list)
    build_doctree(tree, 'confluent_kafka.', confluent_kafka)

    fails = 0
    expect_refs = defaultdict(list)
    all_docs = ''

    int_types = [int]
    if sys.version_info < (3, 0):
        int_types.append(long)  # noqa - long not defined in python2

    for n, vs in tree.items():
        level = 'ERROR'
        err = None

        if len(vs) > 1:
            err = 'Multiple definitions of %s: %s' % (n, vs)
        else:
            o = vs[0]
            doc = o.__doc__
            shortname = n.split('.')[-1]
            if n.find('KafkaException') != -1:
                # Ignore doc-less BaseException inheritance
                err = None
            elif doc is None:
                err = 'Missing __doc__ for: %s (type %s)' % (n, type(o))
            elif not re.search(r':', doc):
                err = 'Missing Doxygen tag for: %s (type %s):\n---\n%s\n---' % (n, type(o), doc)
                if n == 'confluent_kafka.cimpl':
                    # Ignore missing doc strings for the cimpl module itself.
                    level = 'IGNORE'
                elif type(o) in int_types:
                    # Integer constants can't have a doc strings so we check later
                    # that they are referenced somehow in the overall docs.
                    expect_refs[shortname].append(err)
                    err = None
                else:
                    pass
            else:
                all_docs += doc

        if err is not None:
            print('%s: %s' % (level, err))
            if level == 'ERROR':
                fails += 1

    # Make sure constants without docstrings (they can have any)
    # are referenced in other docstrings somewhere.
    for n in expect_refs:
        if all_docs.find(n) == -1:
            print('ERROR: %s not referenced in documentation (%s)' % (n, expect_refs[n]))
            fails += 1

    assert fails == 0

def test_logging_consumer():
    """ Tests that logging works """

    logger = logging.getLogger('consumer')
    logger.setLevel(logging.DEBUG)
    f = CountingFilter('consumer')
    logger.addFilter(f)

    kc = confluent_kafka.Consumer({'group.id': 'test',
                                   'debug': 'all'},
                                  logger=logger)
    while f.cnt == 0:
        kc.poll(timeout=0.5)

    print('%s: %d log messages seen' % (f.name, f.cnt))

    kc.close()


def test_logging_avro_consumer():
    """ Tests that logging works """

    logger = logging.getLogger('avroconsumer')
    logger.setLevel(logging.DEBUG)
    f = CountingFilter('avroconsumer')
    logger.addFilter(f)

    kc = confluent_kafka.avro.AvroConsumer({'schema.registry.url': 'http://example.com',
                                            'group.id': 'test',
                                            'debug': 'all'},
                                           logger=logger)
    while f.cnt == 0:
        kc.poll(timeout=0.5)

    print('%s: %d log messages seen' % (f.name, f.cnt))

    kc.close()


def test_logging_producer():
    """ Tests that logging works """

    logger = logging.getLogger('producer')
    logger.setLevel(logging.DEBUG)
    f = CountingFilter('producer')
    logger.addFilter(f)

    p = confluent_kafka.Producer({'debug': 'all'}, logger=logger)

    while f.cnt == 0:
        p.poll(timeout=0.5)

    print('%s: %d log messages seen' % (f.name, f.cnt))


def test_logging_avro_producer():
    """ Tests that logging works """

    logger = logging.getLogger('avroproducer')
    logger.setLevel(logging.DEBUG)
    f = CountingFilter('avroproducer')
    logger.addFilter(f)

    p = confluent_kafka.avro.AvroProducer({'schema.registry.url': 'http://example.com',
                                           'debug': 'all'},
                                          logger=logger)

    while f.cnt == 0:
        p.poll(timeout=0.5)

    print('%s: %d log messages seen' % (f.name, f.cnt))


def test_logging_constructor():
    """ Verify different forms of constructors """

    for how in ['dict', 'dict+kwarg', 'kwarg']:
        logger = logging.getLogger('producer: ' + how)
        logger.setLevel(logging.DEBUG)
        f = CountingFilter(logger.name)
        logger.addFilter(f)

        if how == 'dict':
            p = confluent_kafka.Producer({'debug': 'all', 'logger': logger})
        elif how == 'dict+kwarg':
            p = confluent_kafka.Producer({'debug': 'all'}, logger=logger)
        elif how == 'kwarg':
            conf = {'debug': 'all', 'logger': logger}
            p = confluent_kafka.Producer(**conf)
        else:
            raise RuntimeError('Not reached')

        print('Test %s with %s' % (p, how))

        while f.cnt == 0:
            p.poll(timeout=0.5)

        print('%s: %s: %d log messages seen' % (how, f.name, f.cnt))


def test_producer_logger_logging_in_given_format():
    """Test that asserts that logging is working by matching part of the log message"""

    stringBuffer = StringIO()
    logger = logging.getLogger('Producer')
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(stringBuffer)
    handler.setFormatter(logging.Formatter('%(name)s Logger | %(message)s'))
    logger.addHandler(handler)

    p = confluent_kafka.Producer(
        {"bootstrap.servers": "test", "logger": logger, "debug": "msg"})
    val = 1
    while val > 0:
        val = p.flush()
    logMessage = stringBuffer.getvalue().strip()
    stringBuffer.close()
    print(logMessage)

    assert "Producer Logger | INIT" in logMessage


def test_consumer_logger_logging_in_given_format():
    """Test that asserts that logging is working by matching part of the log message"""

    stringBuffer = StringIO()
    logger = logging.getLogger('Consumer')
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(stringBuffer)
    handler.setFormatter(logging.Formatter('%(name)s Logger | %(message)s'))
    logger.addHandler(handler)

    c = confluent_kafka.Consumer(
        {"bootstrap.servers": "test", "group.id": "test", "logger": logger, "debug": "msg"})
    c.poll(0)

    logMessage = stringBuffer.getvalue().strip()
    stringBuffer.close()
    c.close()

    assert "Consumer Logger | INIT" in logMessage

def test_error_cb():
    """ Tests error_cb. """
    seen_error_cb = False

    def error_cb(error_msg):
        nonlocal seen_error_cb
        seen_error_cb = True
        acceptable_error_codes = (confluent_kafka.KafkaError._TRANSPORT, confluent_kafka.KafkaError._ALL_BROKERS_DOWN)
        assert error_msg.code() in acceptable_error_codes

    conf = {'bootstrap.servers': 'localhost:65531',  # Purposely cause connection refused error
            'group.id': 'test',
            'session.timeout.ms': 1000,  # Avoid close() blocking too long
            'error_cb': error_cb
            }

    kc = confluent_kafka.Consumer(**conf)
    kc.subscribe(["test"])
    while not seen_error_cb:
        kc.poll(timeout=0.1)

    kc.close()


def test_stats_cb():
    """ Tests stats_cb. """
    seen_stats_cb = False

    def stats_cb(stats_json_str):
        nonlocal seen_stats_cb
        seen_stats_cb = True
        stats_json = json.loads(stats_json_str)
        assert len(stats_json['name']) > 0

    conf = {'group.id': 'test',
            'session.timeout.ms': 1000,  # Avoid close() blocking too long
            'statistics.interval.ms': 200,
            'stats_cb': stats_cb
            }

    kc = confluent_kafka.Consumer(**conf)

    kc.subscribe(["test"])
    while not seen_stats_cb:
        kc.poll(timeout=0.1)
    kc.close()


def test_conf_none():
    """ Issue #133
    Test that None can be passed for NULL by setting bootstrap.servers
    to None. If None would be converted to a string then a broker would
    show up in statistics. Verify that it doesnt. """
    seen_stats_cb_check_no_brokers = False

    def stats_cb_check_no_brokers(stats_json_str):
        """ Make sure no brokers are reported in stats """
        nonlocal seen_stats_cb_check_no_brokers
        stats = json.loads(stats_json_str)
        assert len(stats['brokers']) == 0, "expected no brokers in stats: %s" % stats_json_str
        seen_stats_cb_check_no_brokers = True

    conf = {'bootstrap.servers': None,  # overwrites previous value
            'statistics.interval.ms': 10,
            'stats_cb': stats_cb_check_no_brokers}

    p = confluent_kafka.Producer(conf)
    p.poll(timeout=0.1)

    assert seen_stats_cb_check_no_brokers


def throttle_cb_instantiate_fail():
    """ Ensure noncallables raise TypeError"""
    with pytest.raises(ValueError):
        confluent_kafka.Producer({'throttle_cb': 1})


def throttle_cb_instantiate():
    """ Ensure we can configure a proper callback"""

    def throttle_cb(throttle_event):
        pass

    confluent_kafka.Producer({'throttle_cb': throttle_cb})


def test_throttle_event_types():
    throttle_event = confluent_kafka.ThrottleEvent("broker", 0, 10.0)
    assert isinstance(throttle_event.broker_name, str) and throttle_event.broker_name == "broker"
    assert isinstance(throttle_event.broker_id, int) and throttle_event.broker_id == 0
    assert isinstance(throttle_event.throttle_time, float) and throttle_event.throttle_time == 10.0
    assert str(throttle_event) == "broker/0 throttled for 10000 ms"


def test_oauth_cb():
    """ Tests oauth_cb. """
    seen_oauth_cb = False

    def oauth_cb(oauth_config):
        nonlocal seen_oauth_cb
        seen_oauth_cb = True
        assert oauth_config == 'oauth_cb'
        return 'token', time.time() + 300.0

    conf = {'group.id': 'test',
            'security.protocol': 'sasl_plaintext',
            'sasl.mechanisms': 'OAUTHBEARER',
            'session.timeout.ms': 1000,  # Avoid close() blocking too long
            'sasl.oauthbearer.config': 'oauth_cb',
            'oauth_cb': oauth_cb
            }

    kc = confluent_kafka.Consumer(**conf)

    while not seen_oauth_cb:
        kc.poll(timeout=0.1)
    kc.close()


def test_oauth_cb_principal_sasl_extensions():
    """ Tests oauth_cb. """
    seen_oauth_cb = False

    def oauth_cb(oauth_config):
        nonlocal seen_oauth_cb
        seen_oauth_cb = True
        assert oauth_config == 'oauth_cb'
        return 'token', time.time() + 300.0, oauth_config, {"extone": "extoneval", "exttwo": "exttwoval"}

    conf = {'group.id': 'test',
            'security.protocol': 'sasl_plaintext',
            'sasl.mechanisms': 'OAUTHBEARER',
            'session.timeout.ms': 100,  # Avoid close() blocking too long
            'sasl.oauthbearer.config': 'oauth_cb',
            'oauth_cb': oauth_cb
            }

    kc = confluent_kafka.Consumer(**conf)

    while not seen_oauth_cb:
        kc.poll(timeout=0.1)
    kc.close()


def test_oauth_cb_failure():
    """ Tests oauth_cb. """
    oauth_cb_count = 0

    def oauth_cb(oauth_config):
        nonlocal oauth_cb_count
        oauth_cb_count += 1
        assert oauth_config == 'oauth_cb'
        if oauth_cb_count == 2:
            return 'token', time.time() + 100.0, oauth_config, {"extthree": "extthreeval"}
        raise Exception

    conf = {'group.id': 'test',
            'security.protocol': 'sasl_plaintext',
            'sasl.mechanisms': 'OAUTHBEARER',
            'session.timeout.ms': 1000,  # Avoid close() blocking too long
            'sasl.oauthbearer.config': 'oauth_cb',
            'oauth_cb': oauth_cb
            }

    kc = confluent_kafka.Consumer(**conf)

    while oauth_cb_count < 2:
        kc.poll(timeout=0.1)
    kc.close()


def skip_interceptors():
    # Run interceptor test if monitoring-interceptor is found
    for path in ["/usr/lib", "/usr/local/lib", "staging/libs", "."]:
        for ext in [".so", ".dylib", ".dll"]:
            f = os.path.join(path, "monitoring-interceptor" + ext)
            if os.path.exists(f):
                return False

    # Skip interceptor tests
    return True


@pytest.mark.xfail(sys.platform in ('linux2', 'linux'),
                   reason="confluent-librdkafka-plugins packaging issues")
@pytest.mark.skipif(skip_interceptors(),
                    reason="requires confluent-librdkafka-plugins be installed and copied to the current directory")
@pytest.mark.parametrize("init_func", [
    Consumer,
    Producer,
    AdminClient,
])
def test_unordered_dict(init_func):
    """
    Interceptor configs can only be handled after the plugin has been loaded not before.
    """
    client = init_func({'group.id': 'test-group',
                        'confluent.monitoring.interceptor.publishMs': 1000,
                        'confluent.monitoring.interceptor.sessionDurationMs': 1000,
                        'plugin.library.paths': 'monitoring-interceptor',
                        'confluent.monitoring.interceptor.topic': 'confluent-kafka-testing',
                        'confluent.monitoring.interceptor.icdebug': False})

    client.poll(0)


def test_topic_config_update():
    seen_delivery_cb = False

    # *NOTE* default.topic.config has been deprecated.
    # This example remains to ensure backward-compatibility until its removal.
    confs = [{"message.timeout.ms": 600000, "default.topic.config": {"message.timeout.ms": 1000}},
             {"message.timeout.ms": 1000},
             {"default.topic.config": {"message.timeout.ms": 1000}}]

    def on_delivery(err, msg):
        # Since there is no broker, produced messages should time out.
        nonlocal seen_delivery_cb
        seen_delivery_cb = True
        assert err.code() == confluent_kafka.KafkaError._MSG_TIMED_OUT

    for conf in confs:
        p = confluent_kafka.Producer(conf)

        start = time.time()

        timeout = start + 10.0

        p.produce('mytopic', value='somedata', key='a key', on_delivery=on_delivery)
        while time.time() < timeout:
            if seen_delivery_cb:
                return
            p.poll(1.0)

        if "CI" in os.environ:
            pytest.xfail("Timeout exceeded")
        pytest.fail("Timeout exceeded")


def test_set_sasl_credentials_api():
    clients = [
        AdminClient({}),
        confluent_kafka.Consumer({"group.id": "dummy"}),
        confluent_kafka.Producer({})]

    for c in clients:
        c.set_sasl_credentials('username', 'password')

        c.set_sasl_credentials('override', 'override')

        with pytest.raises(TypeError):
            c.set_sasl_credentials(None, 'password')

        with pytest.raises(TypeError):
            c.set_sasl_credentials('username', None)


def thread_run(myid, p, q):
    def do_crash(err, msg):
        raise IntendedException()

    for i in range(1, 3):
        cb = None
        if i == 2:
            cb = do_crash
        p.produce('mytopic', value='hi', callback=cb)
        t = time.time()
        try:
            p.flush()
            print(myid, 'Flush took %.3f' % (time.time() - t))
        except IntendedException:
            print(myid, "Intentional callback crash: ok")
            continue

    print(myid, 'Done')
    q.put(myid)


def test_thread_safety():
    """ Basic thread safety tests. """

    q = Queue()
    p = Producer({'socket.timeout.ms': 10,
                  'message.timeout.ms': 10})

    threads = list()
    for i in range(1, 5):
        thr = threading.Thread(target=thread_run, name=str(i), args=[i, p, q])
        thr.start()
        threads.append(thr)

    for thr in threads:
        thr.join()

    # Count the number of threads that exited cleanly
    cnt = 0
    try:
        for x in iter(q.get_nowait, None):
            cnt += 1
    except Empty:
        pass

    if cnt != len(threads):
        raise Exception('Only %d/%d threads succeeded' % (cnt, len(threads)))

    print('Done')

class DpAppTests(unittest.TestCase):

    def setUp(self):
        desired_caps = {}
        desired_caps['platformName'] = 'Android'
        desired_caps['platformVersion'] = '4.4'
        desired_caps['deviceName'] = 'emulator-5554'
        desired_caps['autoLaunch'] = 'true'
  #      desired_caps['automationName'] = "selendroid"
        desired_caps['app'] = PATH(
            'apps/Nova_7.2.0_debug.apk'
        )
        desired_caps['appPackage'] = 'com.dianping.v1'
        desired_caps[
            'appActivity'] = 'com.dianping.main.guide.SplashScreenActivity'

        self.driver = webdriver.Remote(
            'http://localhost:4723/wd/hub', desired_caps)

    def tearDown(self):
        self.driver.quit()

    def test_dpApp(self):
        time.sleep(10)
        el = self.driver.find_element_by_xpath(
            "//android.widget.TextView[contains(@text,'美食')]")
        el.click()

class repos(object):

    """download linux repos from mirrors' site."""

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh) Gecko/20100101 Firefox/42.0'}
    urls_dict = {}

    def __init__(self, base_url, base_dir):
        super(repos, self).__init__()
        self.base_url = base_url
        self.base_dir = base_dir

    def download(self):
        for i in self.urls_dict:
            for j in self.urls_dict[i]['files']:
                url = self.base_url + i + j
                print(url)
                request = requests.get(url, headers=self.headers)
                if request.ok:
                    file_location = self.base_dir + i + j

                    if not os.path.exists(self.base_dir + i):
                        os.makedirs(self.base_dir + i)
                    with open(file_location, "wb") as the_file:
                        the_file.write(request.content)

    def get_urls_dict(self, path='/', parent=None):
        if path not in self.urls_dict:
            self.urls_dict[path] = {
                'parent': parent, 'sub_dirs': [], 'files': []}
            url = self.base_url + path
            request = requests.get(url, headers=self.headers)
            if request.ok:
                soup = BeautifulSoup(request.text, 'html.parser')
                for url in soup.find_all('a'):
                    url_text = unquote(url.get('href'))
                    if url_text.endswith('/') and url_text != '/' and url_text != '../':
                        self.urls_dict[path]['sub_dirs'].append(url_text)
                    elif not url_text.endswith('/') and not url_text.startswith('?'):
                        self.urls_dict[path]['files'].append(url_text)
        if self.urls_dict[path]['parent'] == None and len(self.urls_dict[path]['sub_dirs']) == 0:
            pass
        elif len(self.urls_dict[path]['sub_dirs']) != 0:
            for i in self.urls_dict[path]['sub_dirs']:
                return self.get_urls_dict(path=path + i, parent=path)
        elif self.urls_dict[path]['parent'] != None and len(self.urls_dict[path]['sub_dirs']) == 0:
            self.urls_dict[self.urls_dict[path]['parent']][
                'sub_dirs'].remove(path.split('/')[-2] + '/')
            return self.get_urls_dict(path=self.urls_dict[path]['parent'],
                                      parent=self.urls_dict[self.urls_dict[path]['parent']]['parent'])


def my_range(start, end=None, step=1):
    result = []
    if not isinstance(start, int):
        return 'start argument must be an integer.'
    if (not isinstance(end, int)) and (not end is None):
        return 'end argument must be an integer.'
    if not isinstance(step, int):
        return 'step argument must be an integer.'
    elif step == 0:
        return 'step argument must not be zero.'
    if isinstance(end, int):
        while True:
            if start < end:
                result.append(start)
                start += step
            else:
                break
    else:  # end is None
        start, end = 0, start
        while True:
            if start < end:
                result.append(start)
                start += step
            else:
                break
    return result


# 跟range函数的实现基本一样,只是使用yield关键字表示生成器
def my_xrange(start, end=None, step=1):
    if not isinstance(start, int):
        pass
    if (not isinstance(end, int)) and (not end is None):
        pass
    if not isinstance(step, int):
        pass
    elif step == 0:
        pass
    if isinstance(end, int):
        while True:
            if start < end:
                yield start
                start += step
            else:
                break
    else:  # end is None
        start, end = 0, start
        while True:
            if start < end:
                yield start
                start += step
            else:
                break


def exec_cmd(cmd):
    ''' exec a cmd on a remote linux system '''
    for h in hostname_list:
        try:
            client = paramiko.SSHClient()
            client.load_system_host_keys()
            client.set_missing_host_key_policy(paramiko.MissingHostKeyPolicy)
            print('connecting: %s' % h)
            client.connect(h, port=port, username=username, password=password,
                           timeout=5)
            # 多次执行命令 可复用同一个Channel
            chan = client.get_transport().open_session()
            print('exec cmd: %s' % cmd)
            chan.exec_command(cmd)
            print('exit code: %d' % chan.recv_exit_status())
            if chan.recv_exit_status() == 0:
                print('%s OK' % h)
            else:
                print('%s Error!' % h)
            print(chan.recv(200).strip())
            # stdin, stdout, stderr = client.exec_command(cmd)
            # print(stdout.read().strip())
            # print(stderr.read().strip())
        except Exception as e:
            print(e)
        finally:
            chan.close()
            client.close()

class SimpleHTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):

    """Simple HTTP request handler with GET/HEAD/POST commands.

    This serves files from the current directory and any of its
    subdirectories.  The MIME type for files is determined by
    calling the .guess_type() method. And can reveive file uploaded
    by client.

    The GET/HEAD/POST requests are identical except that the HEAD
    request omits the actual contents of the file.

    """

    server_version = "SimpleHTTPWithUpload/" + __version__

    def do_GET(self):
        """Serve a GET request."""
        f = self.send_head()
        if f:
            self.copyfile(f, self.wfile)
            f.close()

    def do_HEAD(self):
        """Serve a HEAD request."""
        f = self.send_head()
        if f:
            f.close()

    def do_POST(self):
        """Serve a POST request."""
        r, info = self.deal_post_data()

        f = StringIO()
        f.write('<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">')
        f.write("<html>\n<title>Upload Result Page</title>\n")
        f.write("<body>\n<h2>Upload Result Page</h2>\n")
        f.write("<hr>\n")
        if r:
            f.write("<strong>Success:</strong>")
        else:
            f.write("<strong>Failed:</strong>")
        f.write(info)
        f.write("<br><a href=\"%s\">back</a>" % self.headers['referer'])
        f.write("<hr><small>Powered By: bones7456, check new version at ")
        f.write("<a href=\"http://li2z.cn/?s=SimpleHTTPServerWithUpload\">")
        f.write("here</a>.</small></body>\n</html>\n")
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        if f:
            self.copyfile(f, self.wfile)
            f.close()

    def deal_post_data(self):
        boundary = self.headers.plisttext.split("=")[1]
        remainbytes = int(self.headers['content-length'])
        line = self.rfile.readline()
        remainbytes -= len(line)
        if boundary not in line:
            return (False, "Content NOT begin with boundary")
        line = self.rfile.readline()
        remainbytes -= len(line)
        fn = re.findall(r'Content-Disposition.*name="file"; filename="(.*)"', line)
        if not fn:
            return (False, "Can't find out file name...")
        path = self.translate_path(self.path)
        fn = os.path.join(path, fn[0])
        while os.path.exists(fn):
            fn += "_"
        line = self.rfile.readline()
        remainbytes -= len(line)
        line = self.rfile.readline()
        remainbytes -= len(line)
        try:
            out = open(fn, 'wb')
        except IOError:
            return (False, "Can't create file to write, do you have permission to write?")

        preline = self.rfile.readline()
        remainbytes -= len(preline)
        while remainbytes > 0:
            line = self.rfile.readline()
            remainbytes -= len(line)
            if boundary in line:
                preline = preline[0:-1]
                if preline.endswith('\r'):
                    preline = preline[0:-1]
                out.write(preline)
                out.close()
                return (True, "File '%s' upload success!" % fn)
            else:
                out.write(preline)
                preline = line
        return (False, "Unexpect Ends of data.")

    def send_head(self):
        """Common code for GET and HEAD commands.

        This sends the response code and MIME headers.

        Return value is either a file object (which has to be copied
        to the outputfile by the caller unless the command was HEAD,
        and must be closed by the caller under all circumstances), or
        None, in which case the caller has nothing further to do.

        """
        path = self.translate_path(self.path)
        f = None
        if os.path.isdir(path):
            if not self.path.endswith('/'):
                # redirect browser - doing basically what apache does
                self.send_response(301)
                self.send_header("Location", self.path + "/")
                self.end_headers()
                return None
            for index in "index.html", "index.htm":
                index = os.path.join(path, index)
                if os.path.exists(index):
                    path = index
                    break
            else:
                return self.list_directory(path)
        ctype = self.guess_type(path)
        try:
            # Always read in binary mode. Opening files in text mode may cause
            # newline translations, making the actual size of the content
            # transmitted *less* than the content-length!
            f = open(path, 'rb')
        except IOError:
            self.send_error(404, "File not found")
            return None
        self.send_response(200)
        self.send_header("Content-type", ctype)
        fs = os.fstat(f.fileno())
        self.send_header("Content-Length", str(fs[6]))
        self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
        self.end_headers()
        return f

    def list_directory(self, path):
        """Helper to produce a directory listing (absent index.html).

        Return value is either a file object, or None (indicating an
        error).  In either case, the headers are sent, making the
        interface the same as for send_head().

        """
        try:
            list = os.listdir(path)
        except os.error:
            self.send_error(404, "No permission to list directory")
            return None
        list.sort(key=lambda a: a.lower())
        f = StringIO()
        displaypath = cgi.escape(urllib.unquote(self.path))
        f.write('<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">')
        f.write("<html>\n<title>Directory listing for %s</title>\n" % displaypath)
        f.write("<body>\n<h2>Directory listing for %s</h2>\n" % displaypath)
        f.write("<hr>\n")
        f.write("<form ENCTYPE=\"multipart/form-data\" method=\"post\">")
        f.write("<input name=\"file\" type=\"file\"/>")
        f.write("<input type=\"submit\" value=\"upload\"/></form>\n")
        f.write("<hr>\n<ul>\n")
        for name in list:
            fullname = os.path.join(path, name)
            displayname = linkname = name
            # Append / for directories or @ for symbolic links
            if os.path.isdir(fullname):
                displayname = name + "/"
                linkname = name + "/"
            if os.path.islink(fullname):
                displayname = name + "@"
                # Note: a link to a directory displays with @ and links with /
            f.write('<li><a href="%s">%s</a>\n'
                    % (urllib.quote(linkname), cgi.escape(displayname)))
        f.write("</ul>\n<hr>\n</body>\n</html>\n")
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        return f

    def translate_path(self, path):
        """Translate a /-separated PATH to the local filename syntax.

        Components that mean special things to the local file system
        (e.g. drive or directory names) are ignored.  (XXX They should
        probably be diagnosed.)

        """
        # abandon query parameters
        path = path.split('?', 1)[0]
        path = path.split('#', 1)[0]
        path = posixpath.normpath(urllib.unquote(path))
        words = path.split('/')
        words = filter(None, words)
        path = os.getcwd()
        for word in words:
            drive, word = os.path.splitdrive(word)
            head, word = os.path.split(word)
            if word in (os.curdir, os.pardir):
                continue
            path = os.path.join(path, word)
        return path

    def copyfile(self, source, outputfile):
        """Copy all data between two file objects.

        The SOURCE argument is a file object open for reading
        (or anything with a read() method) and the DESTINATION
        argument is a file object open for writing (or
        anything with a write() method).

        The only reason for overriding this would be to change
        the block size or perhaps to replace newlines by CRLF
        -- note however that this the default server uses this
        to copy binary data as well.

        """
        shutil.copyfileobj(source, outputfile)

    def guess_type(self, path):
        """Guess the type of a file.

        Argument is a PATH (a filename).

        Return value is a string of the form type/subtype,
        usable for a MIME Content-type header.

        The default implementation looks the file's extension
        up in the table self.extensions_map, using application/octet-stream
        as a default; however it would be permissible (if
        slow) to look inside the data to make a better guess.

        """

        base, ext = posixpath.splitext(path)
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        ext = ext.lower()
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        else:
            return self.extensions_map['']

    if not mimetypes.inited:
        mimetypes.init()  # try to read system mime.types
    extensions_map = mimetypes.types_map.copy()
    extensions_map.update({
        '': 'application/octet-stream',  # Default
        '.py': 'text/plain',
        '.c': 'text/plain',
        '.h': 'text/plain',
        })


def test(HandlerClass=SimpleHTTPRequestHandler,
         ServerClass=BaseHTTPServer.HTTPServer):
    BaseHTTPServer.test(HandlerClass, ServerClass)

def capture(url, img_file="test1.png"):
    safari = webdriver.Safari()
    safari.set_window_size(1200, 900)
    safari.get(url)
    safari.execute_script("""
        (function () {
            var y = 0;
            var step = 100;
            window.scroll(0, 0);

            function f() {
                if (y < document.body.scrollHeight) {
                    y += step;
                    window.scroll(0, y);
                    setTimeout(f, 50);
                } else {
                    window.scroll(0, 0);
                    document.title += "scroll-done";
                }
            }

            setTimeout(f, 1000);
        })();
    """)

    for i in xrange(30):
        if "scroll-done" in safari.title:
            break
        time.sleep(1)

    safari.save_screenshot(img_file)
    safari.close()

def add_remove(tlist, opt_list):
    '''
    add/remove item in tlist.
    opt_list is a list like ['+ts5', '-ts2'] or ['+tc5', '-tc3'].
    '''
    flag = 0
    for i in opt_list:
        i = i.strip()
        if i.startswith('+'):
            tlist.append(i[1:])
        elif i.startswith('-'):
            if i[1:] in tlist:
                tlist.remove(i[1:])
            else:
                flag = 1
        else:
            flag = 1
    if flag:
        return flag
    else:
        return tlist

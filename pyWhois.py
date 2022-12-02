#!/usr/bin/python2.7

from dns.resolver import dns
import argparse, ipwhois, os, re, sys, pythonwhois
import sqlite3 as lite

def cSearch(domain):
    """Grab RRs"""
    multi = grab(domain)
    with open('aTmp', 'w') as aFile:
        with open('mTmp', 'w') as mFile:
            with open('nTmp', 'w') as nFile:
                for answer in multi.answer:
                    if answer.match(answer.name, dns.rdataclass.IN, dns.rdatatype.A, dns.rdatatype.NONE):
                        aFile.write(str(answer) + '\n')
                    if answer.match(answer.name, dns.rdataclass.IN, dns.rdatatype.MX, dns.rdatatype.NONE):
                        mFile.write(str(answer) + '\n')
                    if answer.match(answer.name, dns.rdataclass.IN, dns.rdatatype.NS, dns.rdatatype.NONE):
                        nFile.write(str(answer) + '\n')


def dbGen(dbName = 'clients.sqlite'):
    """DB Creation"""
    try:
        con = lite.connect(dbName)
        db = con.cursor()
        db.execute("CREATE TABLE IF NOT EXISTS domains(dm TEXT, cd TEXT, ed TEXT, UNIQUE(dm))")
        db.execute("CREATE TABLE IF NOT EXISTS hProvider(hp TEXT, UNIQUE(hp))")
        db.execute("CREATE TABLE IF NOT EXISTS ip(ip TEXT, UNIQUE(ip))")
        db.execute("CREATE TABLE IF NOT EXISTS mailservers(mx TEXT, UNIQUE(mx))")
        db.execute("CREATE TABLE IF NOT EXISTS nameservers(ns TEXT, UNIQUE(ns))")
        db.execute("CREATE TABLE IF NOT EXISTS registrars(r TEXT, UNIQUE(r))")
        db.execute("CREATE TABLE IF NOT EXISTS dm2a(dm TEXT, a TEXT, UNIQUE(a))")
        db.execute("CREATE TABLE IF NOT EXISTS dm2mx(dm TEXT, mx TEXT, UNIQUE(mx))")
        db.execute("CREATE TABLE IF NOT EXISTS dm2ns(dm TEXT, ns TEXT, UNIQUE(ns))")
        db.execute("CREATE TABLE IF NOT EXISTS dm2r(dm TEXT, r TEXT, UNIQUE(r))")
        db.execute("CREATE TABLE IF NOT EXISTS dm2hp(dm TEXT, hp TEXT, UNIQUE(hp))")
        con.close()
        con = None
    except lite.Error, e:
        print 'Error %s:' % e.args[0]


def dbUpdate(domain, dbName = 'clients.sqlite'):
    """Add a new client"""
    con = lite.connect(dbName)
    con.text_factory = str
    db = con.cursor()

    ## Grab Registrar object
    r, cd, ed = regPull(domain)

    ## Enter data to the DB
    with con:
        db.execute("INSERT OR IGNORE INTO domains VALUES(?, ?, ?);", (domain, cd.isoformat(), ed.isoformat()))
        db.execute("INSERT OR IGNORE INTO registrars VALUES(?);", (r,))
        db.execute("INSERT OR IGNORE INTO dm2r VALUES(?, ?);", (domain, r))

        with open('aTmp', 'r') as iFile:
            lines = iFile.readlines()
            for i in lines:
                hp = hostInfo(re.sub('\.$', '', i.split(' ')[4].strip()))
                db.execute("INSERT OR IGNORE INTO dm2a VALUES(?, ?);", (domain, re.sub('\.$', '', i.split(' ')[4].strip())))
                db.execute("INSERT OR IGNORE INTO ip VALUES(?);", (re.sub('\.$', '', i.split(' ')[4].strip()),))
                db.execute("INSERT OR IGNORE INTO hProvider VALUES(?);", (hp,))
                db.execute("INSERT OR IGNORE INTO dm2hp VALUES(?, ?);", (domain, hp))

        with open('mTmp', 'r') as iFile:
            lines = iFile.readlines()
            for i in lines:
                db.execute("INSERT OR IGNORE INTO dm2mx VALUES(?, ?);", (domain, re.sub('\.$', '', i.split(' ')[5].strip())))
                db.execute("INSERT OR IGNORE INTO mailservers VALUES(?);", (re.sub('\.$', '', i.split(' ')[5].strip()),))

        with open('nTmp', 'r') as iFile:
            lines = iFile.readlines()
            for i in lines:
                db.execute("INSERT OR IGNORE INTO dm2ns VALUES(?, ?);", (domain, re.sub('\.$', '', i.split(' ')[4].strip())))
                db.execute("INSERT OR IGNORE INTO nameservers VALUES(?);", (re.sub('\.$', '', i.split(' ')[4].strip()),))


def grab(domain):
    """Use Google to grab RRs"""
    name_server = '8.8.8.8'
    ADDITIONAL_RDCLASS = 65535
    request = dns.message.make_query(domain, dns.rdatatype.ANY)
    request.flags |= dns.flags.AD
    request.find_rrset(request.additional, dns.name.root, ADDITIONAL_RDCLASS,
                       dns.rdatatype.OPT, create=True, force_unique=True)
    return dns.query.udp(request, name_server)


#def tGrab(domain):
    #def dQuery(rType):
        #for i in rType:
            #print i
            #print domain
            #for data in dns.resolver.query(domain, i):
                #print data
    #return dQuery


def hostInfo(ip):
    obj = ipwhois.IPWhois(ip)
    lookup = obj.lookup_whois()
    lList = lookup.get('nets')
    return lList[0]['description']


def main(args):
    ## Sanity check
    if args.n is None:
        sys.exit(1)

    ## Create the DB if None
    dbGen()

    ## Grab client infos
    cSearch(args.n)

    ## Update the DB
    dbUpdate(args.n)

    ## Cleanup
    os.remove('aTmp')
    os.remove('mTmp')
    os.remove('nTmp')

    ## Verbosity
    vShow(args.n)


def menu():
    """Help menu"""
    if len(sys.argv) > 1:
        pass
    else:
        print '*  ./pyWhois -n <domain>                           *'
        print '*    Add a new domain to the sqlite3 DB            *'
        sys.exit(0)


def regPull(domain):
    """Grab Registrar info"""
    def looper(domain):
        try:
            obj = pythonwhois.get_whois(domain)
            return obj
        except:
            return None

    counter = 0
    while counter < 5:
        obj = looper(domain)
        if obj is None:
            counter += 1
            print 'Download Error'
            if counter == 4:
                sys.exit(0)
        else:
            break

    r = obj.get('registrar')[0]
    cd = obj.get('creation_date')[0]
    ed = obj.get('expiration_date')[0]
    return r, cd, ed


def vShow(domain, dbName = 'clients.sqlite'):
    con = lite.connect(dbName)
    con.text_factory = str
    db = con.cursor()

    ## Dates
    db.execute("SELECT cd FROM domains WHERE dm = ?;", (domain,))
    cd = db.fetchall()
    db.execute("SELECT ed FROM domains WHERE dm = ?;", (domain,))
    ed = db.fetchall()

    ## Hosting Provider
    db.execute("SELECT hp FROM dm2hp WHERE dm = ?;", (domain,))
    hp = db.fetchall()

    ## Registrar
    db.execute("SELECT r FROM dm2r WHERE dm = ?;", (domain,))
    r = db.fetchall()

    ## MX
    db.execute("SELECT mx FROM dm2mx WHERE dm = ?;", (domain,))
    mx = db.fetchall()

    ## NS
    db.execute("SELECT ns FROM dm2ns WHERE dm = ?;", (domain,))
    ns = db.fetchall()

    ## Printout
    print 'Domain:           %s' % domain
    print 'Creation Date:    %s' % cd
    print 'Expiry Date:      %s' % ed
    print 'Hosting Provider: %s' % hp
    print 'Registrar:        %s' % r
    print 'MX:               %s' % mx
    print 'NS:               %s' % ns



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Client Canvassing', prog = 'brush', usage = menu())
    parser.add_argument('-n', help = 'Add a new client')
    parser.add_argument('-v', action = 'store_true', help = 'Query the domain when finished')
    args = parser.parse_args()
    main(args)

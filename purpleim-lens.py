#! /usr/bin/python

from singlet.lens import SingleScopeLens, IconViewCategory, ListViewCategory
from singlet.utils import run_lens

import dbus
from dbus.mainloop.glib import DBusGMainLoop

def first(iterable, default=None):
    if iterable:
        for item in iterable:
            return item
    return default

class PurpleAdapter:

    IM_CONVERSATION_TYPE = 1

    def __init__(self, purpleInterface):
        self.purple = purpleInterface
        self.__buddies = {}
        self.__accounts = []
        self.reload()

    def openConversation(self, buddyId):
        p = self.purple
        acc = p.PurpleBuddyGetAccount(buddyId)
        buddyName = self.__buddies[buddyId].name

        c = None
        for conv in p.PurpleGetIms():
            convName = p.PurpleConversationGetName(conv)
            if convName == buddyName:
                c = conv
                break

        if not c:
            c = p.PurpleConversationNew(self.IM_CONVERSATION_TYPE, acc, buddyName)

        p.PurpleConversationPresent(c)

    def reloadAccounts(self):
        self.__accounts = self.purple.PurpleAccountsGetAllActive()

    def buildBuddy(self, buddyId):
        b = Buddy(buddyId, 
                 self.purple.PurpleBuddyGetAlias(buddyId), 
                 self.purple.PurpleBuddyGetName(buddyId), 
                 self.purple.PurpleBuddyGetIcon(buddyId),
                 self.purple.PurpleBuddyGetAccount(buddyId))
        b.iconPath = self.purple.PurpleBuddyIconGetFullPath(b.icon) if b.icon > 0 else None
        return b

    def reloadBuddies(self):
        self.__buddies = dict([ (x, self.buildBuddy(x)) for x in self.purple.PurpleBlistGetBuddies() ])

    def reload(self):
        self.reloadAccounts()
        self.reloadBuddies()

    def searchBuddies(self, term):
        self.reload()

        if type(term) == unicode:
            term = term.encode('raw_unicode_escape')
        
        uTerm = term.decode('utf-8')
        result = ( item for item in self.__buddies.itervalues() 
                        if item.account in self.__accounts and 
                           uTerm.upper() in item.aliasUpper )
        return result

class Buddy:
    def __init__(self, bId, alias, name, icon, account):
        self.id = bId
        self.name = name
        self.alias = alias
        self.aliasUpper = self.alias.upper()
        self.icon = icon
        self.account = account
        self.iconPath = None

class PurpleBuddyLens(SingleScopeLens):

    class Meta:
        description = "Pidgin lens"
        name = 'purpleim'
        icon = 'purpleim-lens.svg'

    cat = ListViewCategory("Pidgin Contacts", "hint")
    
    uriPrefix = "purple-contact://local"

    mimeType = 'application/x-purple-contact'

    purple = None
        
    def setupPurple(self):
        try:
            main_loop = DBusGMainLoop()
            session_bus = dbus.SessionBus(mainloop = main_loop)
            obj = session_bus.get_object("im.pidgin.purple.PurpleService", "/im/pidgin/purple/PurpleObject")
            self.purple = PurpleAdapter(dbus.Interface(obj, "im.pidgin.purple.PurpleInterface"))
        except Exception as x:
            print x, x.message

    def getBuddyResult(self, buddy):
        return ('%s/%d' % (self.uriPrefix, buddy.id),
                 buddy.iconPath if buddy.iconPath else "stock_person",
                 self.cat,
                 self.mimeType,
                 buddy.alias, 
                 buddy.name)

    def search(self, phrase, results):
        if not self.purple:
            self.setupPurple()

        if self.purple:
            buddies = self.purple.searchBuddies(phrase)

            for buddy in buddies:
                results.append(*self.getBuddyResult(buddy))

    def handle_uri(self, scope, uri):
        self.purple.openConversation(int(uri.split('/')[-1]))
        return self.hide_dash_response()

if __name__ == "__main__":
    import sys
    run_lens(PurpleBuddyLens, sys.argv)

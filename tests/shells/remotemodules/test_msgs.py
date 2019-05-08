from crl.interactivesessions.shells.remotemodules.msgs import MsgBase


__copyright__ = 'Copyright (C) 2019, Nokia'


class CustomMsg(MsgBase):
    @property
    def custom(self):
        return self._arg


class OtherCustomMsg(CustomMsg):
    pass


def test_custommsg():
    MsgBase.set_msgclses(CustomMsg, OtherCustomMsg)
    cmsgs = {}
    for i in range(2):
        cmsgs[i] = CustomMsg.create('custom{}'.format(i))
    ocmsg = OtherCustomMsg.create('othercustom')

    assert cmsgs[0].uid != cmsgs[1].uid
    assert cmsgs[0].msgid == cmsgs[1].msgid

    assert ocmsg.msgid != cmsgs[0].msgid

    s = cmsgs[0].serialize()
    m = MsgBase.deserialize(s)

    assert m.uid == cmsgs[0].uid
    assert m.msgid == cmsgs[0].msgid
    assert m.custom == cmsgs[0].custom

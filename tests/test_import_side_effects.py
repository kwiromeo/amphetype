"""Import-time side-effect contract: importing Data must not open a DB."""
import amphetype.Data


def test_data_import_opens_no_db():
    assert amphetype.Data.DB is None

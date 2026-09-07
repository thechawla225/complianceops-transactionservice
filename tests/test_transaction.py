from app.models.transaction import Transaction

def test_table_name():
    assert Transaction.__tablename__ == "transaction"
    
def test_columns_match_architecture_md_data_model():
    columns = {c.name for c in Transaction.__table__.columns}
    assert columns == {
        "id",
        "end_to_end_id",
        "debtor_name",
        "debtor_agent_bic",
        "creditor_name",
        "creditor_agent_bic",
        "instructed_amount",
        "instructed_currency",
        "remittance_information",
        "status",
        "screening_ref",
        "created_at",
    }
 
 
def test_money_and_currency_columns_are_strings_not_numeric():
    amount_col = Transaction.__table__.columns["instructed_amount"]
    currency_col = Transaction.__table__.columns["instructed_currency"]
    assert amount_col.type.python_type is str
    assert currency_col.type.python_type is str
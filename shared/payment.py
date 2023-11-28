from model import User, Event, Payment
from fastapi import FastAPI, Depends, status, HTTPException
from sqlalchemy.orm.session import Session
from database import SessionLocal, engine

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

#create Payment instances after Event Completion
def create_payment(event: Event, db: Session = Depends(get_db)):
    #check event_id
    if not event:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="無此共乘事件")

    joiner_list = event.joiner.strip(',').split(",")

    for i in range(len(joiner_list)):
        payment = Payment(
            with_draw_or_top_up=0,
            money=calculate_payable(joiner_list[i], event, joiner_list, db),
            event_id=event.id,
            isCompleted=False,
            user_id=joiner_list[i],
        )
        db.add(payment)
        db.commit()
    
    return 1

#calculate the amount of money to be paid by the user_id
def calculate_payable(userid: int, event: Event, joiner_list: list, db: Session = Depends(get_db)):

    joiner_loc = event.joiner_to_location.split(",") #['1-3', '2-3']
    joiner_start_end_loc = [loc.split("-") for loc in joiner_loc]  #[['1', '3'], ['2', '3']]
    total_num_loc = 0

    for i in range(1 if event.is_self_drive else 0, len(joiner_start_end_loc)):
        start_loc, end_loc = int(joiner_start_end_loc[i][0]), int(joiner_start_end_loc[i][1])

        if start_loc >= end_loc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="起始地設定出錯")
        total_num_loc += (end_loc - start_loc)
    
    user_idx_in_joiner = (''.join(joiner_list)).find(str(userid))
    amount_paid = int(joiner_start_end_loc[user_idx_in_joiner][1]) - int(joiner_start_end_loc[user_idx_in_joiner][0])
    total_paid = (amount_paid/total_num_loc) * event.accounts_payable

    return total_paid

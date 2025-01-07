-- check process times for each opportunity
select
buy_source,
sell_source,
DATE_FORMAT(FROM_UNIXTIME(created_at / 1000000), '%d-%m-%Y') as date_created,
(opportunity_check_started_at - buy_source_ticker_time)/1000 as buy_tick_wait_ms,
(opportunity_check_started_at - sell_source_ticker_time)/1000 as sell_tick_wait_ms,
(created_at - opportunity_check_started_at)/1000 as process_time_ms,
(opp_added_to_queue_at - created_at)/1000 as queue_ingress_wait_ms,
(opp_received_in_queue_at - opp_added_to_queue_at)/1000 as queue_wait_ms,
(opp_buy_task_created_at - opp_received_in_queue_at)/1000 as buy_task_create_ms,
(opp_sell_task_created_at - opp_received_in_queue_at)/1000 as sell_task_create_ms,
(opp_buy_task_received_at - opp_buy_task_created_at)/1000 as buy_task_wait_ms,
(opp_sell_task_received_at - opp_sell_task_created_at)/1000 as sell_task_wait_ms,
(buy_ordered_at - opp_buy_task_received_at)/1000 as buy_task_process_ms,
(sell_ordered_at - opp_sell_task_received_at)/1000 as sell_task_process_ms
from arbitrage_opportunities a
where created_at >= 1736101800000000
and created_at <= 1736188200000000
and buy_order_id is not null;
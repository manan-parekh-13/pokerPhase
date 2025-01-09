-- check process times for each opportunity
select
a.id,
i.trading_symbol,
DATE_FORMAT(FROM_UNIXTIME(created_at / 1000000), '%d-%m-%Y') as date_created,
CASE
	when buy_source = i.instrument_token1 then i.exchange1
	 else i.exchange2
end as buy_from,
CASE
	when sell_source = i.instrument_token1 then i.exchange1
	 else i.exchange2
end as sell_to,
-- (opportunity_check_started_at - buy_source_ticker_time)/1000 as buy_tick_wait_ms,
-- (opportunity_check_started_at - sell_source_ticker_time)/1000 as sell_tick_wait_ms,
-- (created_at - opportunity_check_started_at)/1000 as process_time_ms,
-- (opp_added_to_queue_at - created_at)/1000 as queue_ingress_wait_ms,
-- (opp_received_in_queue_at - opp_added_to_queue_at)/1000 as queue_wait_ms,
-- (opp_buy_task_created_at - opp_received_in_queue_at)/1000 as buy_task_create_ms,
-- (opp_sell_task_created_at - opp_received_in_queue_at)/1000 as sell_task_create_ms,
-- (opp_buy_task_received_at - opp_buy_task_created_at)/1000 as buy_task_wait_ms,
-- (opp_sell_task_received_at - opp_sell_task_created_at)/1000 as sell_task_wait_ms,
opportunity_check_started_at - GREATEST(buy_source_ticker_time, sell_source_ticker_time) as wait_latency_us,
GREATEST(opp_buy_task_received_at, opp_sell_task_received_at) - opportunity_check_started_at as process_latency_us,
(buy_ordered_at - opp_buy_task_received_at)/1000 as buy_latency_ms,
(sell_ordered_at - opp_sell_task_received_at)/1000 as sell_latency_ms
from arbitrage_opportunities a
inner join arbitrage_instruments i
on (i.instrument_token1 = a.buy_source or i.instrument_token1 = a.sell_source)
where buy_order_id is not null
order by created_at desc;
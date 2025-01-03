-- daily aggregates table
CREATE TABLE `daily_aggregates` (
  `id` int NOT NULL AUTO_INCREMENT,
  `date_created` varchar(15) not null,
  `trading_symbol` varchar(30) not null,
  `opp_count` int DEFAULT 0,
  `sell_source` int DEFAULT NULL,
  `avg_profit_percent` decimal(6,4) DEFAULT 0.0,
  `std_dev_profit_percent` decimal(6,4) DEFAULT 0.0,
  `total_profit` decimal(10,4) DEFAULT 0.0,
  `avg_buy_value` decimal(10,4) DEFAULT 0.0,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- procedure to get date wise aggregates for stocks
DELIMITER $$

CREATE PROCEDURE calc_day_wise_aggregates(start_date BIGINT, end_date BIGINT)
BEGIN
    INSERT INTO daily_aggregates (
        date_created,
        trading_symbol,
        opp_count,
        avg_profit_percent,
        std_dev_profit_percent,
        total_profit,
        avg_buy_value
    )
    SELECT
        DATE_FORMAT(FROM_UNIXTIME(ap.created_at / 1000000), '%Y-%m-%d') AS date_created,
        i.tradingsymbol AS trading_symbol,
        COUNT(*) AS opp_count,
        ROUND(AVG(
            CASE
                WHEN buy_price * quantity > 66000 THEN
                    (sell_price / buy_price - 47.2 / (buy_price * quantity) - 1.00038) * 100
                ELSE
                    (sell_price / buy_price - 1.0011) * 100
            END
        ), 3) AS avg_profit_percent,
        ROUND(STDDEV_POP(
            CASE
                WHEN buy_price * quantity > 66000 THEN
                    (sell_price / buy_price - 47.2 / (buy_price * quantity) - 1.00038) * 100
                ELSE
                    (sell_price / buy_price - 1.0011) * 100
            END
        ), 3) AS std_dev_profit_percent,
        ROUND(SUM(
            CASE
                WHEN buy_price * quantity > 66000 THEN
                    (sell_price - buy_price) * quantity - 47.2 - 0.00038 * buy_price * quantity
                ELSE
                    (sell_price - buy_price) * quantity - 0.0011 * buy_price * quantity
            END
        ), 3) AS total_profit,
        ROUND(AVG(buy_price * quantity), 3) AS avg_buy_value
    FROM
        arbitrage_opportunities ap
    INNER JOIN
        instruments i
    ON
        i.instrument_token = ap.buy_source
    WHERE
        created_at >= start_date AND created_at <= end_date
    GROUP BY
        DATE_FORMAT(FROM_UNIXTIME(ap.created_at / 1000000), '%Y-%m-%d'),
        i.tradingsymbol;
END$$

DELIMITER ;

-- procedure to calc day wise aggregates in a loop
DELIMITER $$

CREATE PROCEDURE calc_day_wise_aggregates_in_loop(start_date BIGINT, end_date BIGINT)
BEGIN
    DECLARE curr_date BIGINT;
    DECLARE next_date BIGINT;

    SET curr_date = start_date;

    WHILE curr_date <= end_date DO
        SET next_date = curr_date + 86400000000;
        CALL calc_day_wise_aggregates(curr_date, next_date);
        SET curr_date = next_date;
    END WHILE;
END$$

DELIMITER ;

-- event to call the day_wise_aggregate procedure every weekday at 15:35 pm
DELIMITER $$

CREATE EVENT daily_aggregate_event
ON SCHEDULE
    EVERY 1 DAY
    STARTS TIMESTAMP(CURDATE() + INTERVAL (15 - HOUR(NOW())) HOUR + INTERVAL (35 - MINUTE(NOW())) MINUTE)
DO
    BEGIN
        IF DAYOFWEEK(CURDATE()) BETWEEN 2 AND 6 THEN
            CALL calc_day_wise_aggregates(
                UNIX_TIMESTAMP(CURDATE()) * 1000000,
                UNIX_TIMESTAMP(CURDATE() + INTERVAL 1 DAY) * 1000000
            );
        END IF;
    END$$

DELIMITER ;

-- calc avg + 1 std dev for all trading symbols for all of the day wise aggregates to get min profit percent
UPDATE arbitrage_instruments i
JOIN (
    SELECT
        d.trading_symbol,
        COUNT(date_created) AS dateCount,
        ROUND(AVG(avg_profit_percent), 3) AS avg,
        ROUND(STDDEV(avg_profit_percent), 3) AS std_dev,
        ROUND(AVG(avg_profit_percent) + STDDEV(avg_profit_percent), 3) AS avg_plus_one_dev
    FROM daily_aggregates d
    WHERE opp_count > 10
    GROUP BY trading_symbol
    HAVING dateCount > 10
) AS d
ON d.trading_symbol = i.trading_symbol
SET i.min_profit_percent = d.avg_plus_one_dev, i.try_ordering = 1;


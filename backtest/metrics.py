import pandas as pd


class PerformanceMetrics:

    def __init__(self, portfolio):

        self.portfolio = portfolio

    # ==================================================
    # EXPORT TRADES
    # ==================================================

    def export_trades_to_csv(
        self,
        filename="trade_analytics.csv"
    ):

        trades = (
            self.portfolio.closed_trades
        )

        if not trades:

            return None

        rows = []

        for trade in trades:

            row = {

                "symbol":
                    trade.symbol,

                "entry_time":
                    trade.entry_time,

                "exit_time":
                    trade.exit_time,

                "entry_price":
                    trade.entry_price,

                "exit_price":
                    trade.exit_price,

                "quantity":
                    trade.quantity,

                "pnl":
                    trade.pnl,

                "pnl_pct":
                    trade.pnl_pct * 100,

                "exit_reason":
                    trade.exit_reason,

                "score":
                    trade.entry_signal_score,

                "entry_commission":
                    trade.entry_commission,

                "exit_commission":
                    trade.exit_commission,

                "slippage_cost":
                    trade.slippage_cost,
            }

            row.update(
                trade.entry_metrics
            )

            rows.append(row)

        df = pd.DataFrame(
            rows
        )

        df.to_csv(
            filename,
            index=False
        )

        return df

    # ==================================================
    # MAX DRAWDOWN
    # ==================================================

    def calculate_max_drawdown(self):

        equity_df = pd.DataFrame(
            self.portfolio.equity_curve
        )

        if equity_df.empty:

            return 0.0

        if "equity" not in equity_df.columns:

            return 0.0

        equity = pd.to_numeric(
            equity_df["equity"],
            errors="coerce"
        ).dropna()

        if equity.empty:

            return 0.0

        running_max = (
            equity.cummax()
        )

        drawdown = (
            equity
            / running_max
            - 1
        )

        return (
            float(drawdown.min())
            * 100
        )

    # ==================================================
    # DAILY STATISTICS
    # ==================================================

    def calculate_daily_statistics(self):

        equity_df = pd.DataFrame(
            self.portfolio.equity_curve
        )

        if equity_df.empty:

            return {
                "positive_days": 0,
                "negative_days": 0,
                "flat_days": 0,
                "best_day_pct": 0.0,
                "worst_day_pct": 0.0,
                "average_daily_return_pct": 0.0,
            }

        if (
            "timestamp" not in equity_df.columns
            or "equity" not in equity_df.columns
        ):

            return {
                "positive_days": 0,
                "negative_days": 0,
                "flat_days": 0,
                "best_day_pct": 0.0,
                "worst_day_pct": 0.0,
                "average_daily_return_pct": 0.0,
            }

        data = equity_df.copy()

        data["timestamp"] = pd.to_datetime(
            data["timestamp"]
        )

        data["date"] = (
            data["timestamp"].dt.date
        )

        daily = (
            data
            .groupby("date")["equity"]
            .agg(
                first="first",
                last="last"
            )
        )

        if daily.empty:

            return {
                "positive_days": 0,
                "negative_days": 0,
                "flat_days": 0,
                "best_day_pct": 0.0,
                "worst_day_pct": 0.0,
                "average_daily_return_pct": 0.0,
            }

        daily["daily_return_pct"] = (
            (
                daily["last"]
                / daily["first"]
            ) - 1
        ) * 100

        returns = daily[
            "daily_return_pct"
        ]

        positive_days = int(
            (returns > 0).sum()
        )

        negative_days = int(
            (returns < 0).sum()
        )

        flat_days = int(
            (returns == 0).sum()
        )

        return {

            "positive_days":
                positive_days,

            "negative_days":
                negative_days,

            "flat_days":
                flat_days,

            "best_day_pct":
                float(returns.max()),

            "worst_day_pct":
                float(returns.min()),

            "average_daily_return_pct":
                float(returns.mean()),
        }

    # ==================================================
    # STREAK STATISTICS
    # ==================================================

    def calculate_streaks(self):

        trades = (
            self.portfolio.closed_trades
        )

        if not trades:

            return {

                "max_winning_streak":
                    0,

                "max_losing_streak":
                    0,
            }

        current_wins = 0
        current_losses = 0

        max_wins = 0
        max_losses = 0

        for trade in trades:

            pnl = float(
                trade.pnl
            )

            if pnl > 0:

                current_wins += 1
                current_losses = 0

                max_wins = max(
                    max_wins,
                    current_wins
                )

            elif pnl < 0:

                current_losses += 1
                current_wins = 0

                max_losses = max(
                    max_losses,
                    current_losses
                )

            else:

                current_wins = 0
                current_losses = 0

        return {

            "max_winning_streak":
                max_wins,

            "max_losing_streak":
                max_losses,
        }

    # ==================================================
    # EXIT STATISTICS
    # ==================================================

    def calculate_exit_statistics(self):

        trades = (
            self.portfolio.closed_trades
        )

        if not trades:

            return {

                "stop_exits": 0,

                "target_exits": 0,

                "daily_tp2_exits": 0,

                "end_of_backtest_exits": 0,

                "ambiguous_exits": 0,
            }

        exit_reasons = [
            trade.exit_reason
            for trade in trades
        ]

        return {

            "stop_exits":
                sum(
                    reason == "STOP"
                    for reason in exit_reasons
                ),

            "target_exits":
                sum(
                    reason == "TARGET"
                    for reason in exit_reasons
                ),

            "daily_tp2_exits":
                sum(
                    reason == "DAILY_TP2"
                    for reason in exit_reasons
                ),

            "end_of_backtest_exits":
                sum(
                    reason == "END_OF_BACKTEST"
                    for reason in exit_reasons
                ),

            "ambiguous_exits":
                sum(
                    reason
                    == "STOP_AMBIGUOUS_BAR"
                    for reason in exit_reasons
                ),
        }

    # ==================================================
    # MAIN CALCULATION
    # ==================================================

    def calculate(self):

        trades = (
            self.portfolio.closed_trades
        )

        initial_capital = float(
            self.portfolio.initial_capital
        )

        equity_df = pd.DataFrame(
            self.portfolio.equity_curve
        )

        # --------------------------------------------------
        # ENDING EQUITY
        # --------------------------------------------------

        if (
            not equity_df.empty
            and "equity"
            in equity_df.columns
        ):

            ending_capital = float(
                equity_df.iloc[-1]["equity"]
            )

        else:

            ending_capital = float(
                self.portfolio.cash
            )

        # --------------------------------------------------
        # RETURN
        # --------------------------------------------------

        total_return_pct = (

            (
                ending_capital
                / initial_capital
            ) - 1

        ) * 100

        # --------------------------------------------------
        # NO TRADES
        # --------------------------------------------------

        if not trades:

            result = {

                "initial_capital":
                    initial_capital,

                "ending_capital":
                    ending_capital,

                "total_return_pct":
                    total_return_pct,

                "total_trades":
                    0,

                "winning_trades":
                    0,

                "losing_trades":
                    0,

                "win_rate_pct":
                    0.0,

                "profit_factor":
                    0.0,

                "gross_profit":
                    0.0,

                "gross_loss":
                    0.0,

                "average_win":
                    0.0,

                "average_loss":
                    0.0,

                "payoff_ratio":
                    0.0,

                "expectancy":
                    0.0,

                "best_trade":
                    0.0,

                "worst_trade":
                    0.0,

                "average_trade":
                    0.0,

                "max_drawdown_pct":
                    self.calculate_max_drawdown(),
            }

            result.update(
                self.calculate_daily_statistics()
            )

            result.update(
                self.calculate_streaks()
            )

            result.update(
                self.calculate_exit_statistics()
            )

            return result

        # --------------------------------------------------
        # PNL
        # --------------------------------------------------

        pnl = pd.Series(

            [
                float(
                    trade.pnl
                )
                for trade in trades
            ],

            dtype=float
        )

        wins = pnl[
            pnl > 0
        ]

        losses = pnl[
            pnl < 0
        ]

        # --------------------------------------------------
        # COUNTS
        # --------------------------------------------------

        total_trades = len(
            trades
        )

        winning_trades = len(
            wins
        )

        losing_trades = len(
            losses
        )

        # --------------------------------------------------
        # WIN RATE
        # --------------------------------------------------

        win_rate_pct = (

            winning_trades
            / total_trades

        ) * 100

        # --------------------------------------------------
        # GROSS
        # --------------------------------------------------

        gross_profit = float(
            wins.sum()
        )

        gross_loss = abs(
            float(
                losses.sum()
            )
        )

        # --------------------------------------------------
        # PROFIT FACTOR
        # --------------------------------------------------

        if gross_loss > 0:

            profit_factor = (
                gross_profit
                / gross_loss
            )

        else:

            profit_factor = float(
                "inf"
            )

        # --------------------------------------------------
        # AVERAGES
        # --------------------------------------------------

        average_win = (

            float(
                wins.mean()
            )

            if not wins.empty
            else 0.0
        )

        average_loss = (

            float(
                losses.mean()
            )

            if not losses.empty
            else 0.0
        )

        # --------------------------------------------------
        # PAYOFF
        # --------------------------------------------------

        if average_loss != 0:

            payoff_ratio = (

                average_win
                / abs(
                    average_loss
                )

            )

        else:

            payoff_ratio = float(
                "inf"
            )

        # --------------------------------------------------
        # EXPECTANCY
        # --------------------------------------------------

        win_probability = (
            winning_trades
            / total_trades
        )

        loss_probability = (
            losing_trades
            / total_trades
        )

        expectancy = (

            (
                win_probability
                * average_win
            )

            +

            (
                loss_probability
                * average_loss
            )
        )

        # --------------------------------------------------
        # BEST / WORST
        # --------------------------------------------------

        best_trade = float(
            pnl.max()
        )

        worst_trade = float(
            pnl.min()
        )

        # --------------------------------------------------
        # AVERAGE TRADE
        # --------------------------------------------------

        average_trade = float(
            pnl.mean()
        )

        # --------------------------------------------------
        # DRAWDOWN
        # --------------------------------------------------

        max_drawdown_pct = (
            self.calculate_max_drawdown()
        )

        # --------------------------------------------------
        # OTHER STATISTICS
        # --------------------------------------------------

        result = {

            "initial_capital":
                initial_capital,

            "ending_capital":
                ending_capital,

            "total_return_pct":
                total_return_pct,

            "total_trades":
                total_trades,

            "winning_trades":
                winning_trades,

            "losing_trades":
                losing_trades,

            "win_rate_pct":
                win_rate_pct,

            "profit_factor":
                profit_factor,

            "gross_profit":
                gross_profit,

            "gross_loss":
                gross_loss,

            "average_win":
                average_win,

            "average_loss":
                average_loss,

            "payoff_ratio":
                payoff_ratio,

            "expectancy":
                expectancy,

            "best_trade":
                best_trade,

            "worst_trade":
                worst_trade,

            "average_trade":
                average_trade,

            "max_drawdown_pct":
                max_drawdown_pct,
        }

        result.update(
            self.calculate_daily_statistics()
        )

        result.update(
            self.calculate_streaks()
        )

        result.update(
            self.calculate_exit_statistics()
        )

        return result
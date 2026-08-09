import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:owner_mobile/features/reports/data/owner_reports_api_client.dart';
import 'package:owner_mobile/features/reports/domain/dashboard_models.dart';
import 'package:owner_mobile/features/reports/presentation/owner_dashboard_screen.dart';

class MockOwnerReportsApiClient extends Mock implements OwnerReportsApiClient {}

OwnerDashboardModel _dashboard() => const OwnerDashboardModel(
      portfolio: PortfolioSnapshotModel(
        statusCounts: [
          StatusCountModel(status: 'active', count: 1),
          StatusCountModel(status: 'paid', count: 0),
        ],
        totalOriginalPrincipal: '1000.00',
        outstandingPrincipal: '600.00',
        accruedInterest: '25.50',
        totalScheduledInterest: '120.00',
        totalScheduledRepayment: '1120.00',
        nextInterestDue: '10.00',
        activeLoanCount: 1,
        paidLoanCount: 0,
      ),
      collections: CollectionsSummaryModel(
        fromDate: '2026-08-01',
        toDate: '2026-08-31',
        totalPaymentAmount: '700.00',
        principalAllocation: '500.00',
        interestAllocation: '100.00',
        unappliedCreditAllocation: '100.00',
      ),
      accountingBalances: [
        AccountBalanceModel(
          code: '1000',
          name: 'Cash',
          normalBalance: 'debit',
          balance: '700.00',
        ),
      ],
      loanRequestStatusCounts: [
        StatusCountModel(status: 'pending', count: 2),
      ],
    );

OwnerDashboardModel _emptyDashboard() => const OwnerDashboardModel(
      portfolio: PortfolioSnapshotModel(
        statusCounts: [StatusCountModel(status: 'active', count: 0)],
        totalOriginalPrincipal: '0.00',
        outstandingPrincipal: '0.00',
        accruedInterest: '0.00',
        totalScheduledInterest: '0.00',
        totalScheduledRepayment: '0.00',
        nextInterestDue: '0.00',
        activeLoanCount: 0,
        paidLoanCount: 0,
      ),
      collections: CollectionsSummaryModel(
        fromDate: '2026-08-01',
        toDate: '2026-08-31',
        totalPaymentAmount: '0.00',
        principalAllocation: '0.00',
        interestAllocation: '0.00',
        unappliedCreditAllocation: '0.00',
      ),
      accountingBalances: [],
      loanRequestStatusCounts: [
        StatusCountModel(status: 'pending', count: 0),
      ],
    );

void main() {
  late MockOwnerReportsApiClient client;

  setUpAll(() => registerFallbackValue(DateTime(2026, 1, 1)));

  setUp(() {
    client = MockOwnerReportsApiClient();
  });

  Widget app() => ProviderScope(
        overrides: [ownerReportsApiClientProvider.overrideWithValue(client)],
        child: MaterialApp(
          home: OwnerDashboardScreen(initialDate: DateTime(2026, 8, 15)),
        ),
      );

  testWidgets('shows loading then canonical dashboard summaries',
      (tester) async {
    final completer = Completer<OwnerDashboardModel>();
    when(() => client.fetchDashboard(
          fromDate: any(named: 'fromDate'),
          toDate: any(named: 'toDate'),
        )).thenAnswer((_) => completer.future);

    await tester.pumpWidget(app());
    expect(find.byType(CircularProgressIndicator), findsOneWidget);

    completer.complete(_dashboard());
    await tester.pumpAndSettle();

    expect(find.text('Reports & Dashboard'), findsOneWidget);
    expect(find.text('Portfolio'), findsOneWidget);
    expect(find.text('₱600.00'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.text('Total payments'),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    final totalPaymentsRow = find.ancestor(
      of: find.text('Total payments'),
      matching: find.byType(ListTile),
    );
    expect(
      find.descendant(
        of: totalPaymentsRow,
        matching: find.text('₱700.00'),
      ),
      findsOneWidget,
    );
    await tester.scrollUntilVisible(
      find.text('Loan requests'),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    expect(find.text('Loan requests'), findsOneWidget);
  });

  testWidgets('shows error state and retries', (tester) async {
    var calls = 0;
    when(() => client.fetchDashboard(
          fromDate: any(named: 'fromDate'),
          toDate: any(named: 'toDate'),
        )).thenAnswer((_) async {
      calls += 1;
      if (calls == 1) throw Exception('offline');
      return _dashboard();
    });

    await tester.pumpWidget(app());
    await tester.pumpAndSettle();
    expect(find.text('Unable to load dashboard metrics.'), findsOneWidget);

    await tester.tap(find.text('Retry'));
    await tester.pumpAndSettle();
    expect(find.text('Portfolio'), findsOneWidget);
    expect(calls, 2);
  });

  testWidgets('shows explicit empty state', (tester) async {
    when(() => client.fetchDashboard(
          fromDate: any(named: 'fromDate'),
          toDate: any(named: 'toDate'),
        )).thenAnswer((_) async => _emptyDashboard());

    await tester.pumpWidget(app());
    await tester.pumpAndSettle();

    expect(find.text('No report activity for the selected period.'),
        findsOneWidget);
  });

  testWidgets('invalid date range hides stale metrics and blocks refresh',
      (tester) async {
    var calls = 0;
    when(() => client.fetchDashboard(
          fromDate: any(named: 'fromDate'),
          toDate: any(named: 'toDate'),
        )).thenAnswer((_) async {
      calls += 1;
      return _dashboard();
    });

    await tester.pumpWidget(app());
    await tester.pumpAndSettle();
    expect(find.text('Portfolio'), findsOneWidget);

    await tester.tap(find.text('From 2026-08-01'));
    await tester.pumpAndSettle();
    await tester.tap(find.byTooltip('Next month'));
    await tester.pumpAndSettle();
    await tester.tap(find.bySemanticsLabel(RegExp('September 1, 2026')));
    await tester.tap(find.text('OK'));
    await tester.pumpAndSettle();

    expect(
        find.text('Start date must be on or before end date.'), findsOneWidget);
    expect(find.text('Portfolio'), findsNothing);
    expect(calls, 1);

    await tester.tap(find.byTooltip('Refresh dashboard'));
    await tester.pumpAndSettle();
    expect(calls, 1);
  });
}

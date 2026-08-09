class StatusCountModel {
  final String status;
  final int count;

  const StatusCountModel({required this.status, required this.count});

  factory StatusCountModel.fromJson(Map<String, dynamic> json) {
    return StatusCountModel(
      status: json['status'] as String,
      count: json['count'] as int,
    );
  }
}

class PortfolioSnapshotModel {
  final List<StatusCountModel> statusCounts;
  final String totalOriginalPrincipal;
  final String outstandingPrincipal;
  final String accruedInterest;
  final int activeLoanCount;
  final int paidLoanCount;

  const PortfolioSnapshotModel({
    required this.statusCounts,
    required this.totalOriginalPrincipal,
    required this.outstandingPrincipal,
    required this.accruedInterest,
    required this.activeLoanCount,
    required this.paidLoanCount,
  });

  factory PortfolioSnapshotModel.fromJson(Map<String, dynamic> json) {
    return PortfolioSnapshotModel(
      statusCounts: (json['status_counts'] as List<dynamic>)
          .map(
              (item) => StatusCountModel.fromJson(item as Map<String, dynamic>))
          .toList(),
      totalOriginalPrincipal: json['total_original_principal'].toString(),
      outstandingPrincipal: json['outstanding_principal'].toString(),
      accruedInterest: json['accrued_interest'].toString(),
      activeLoanCount: json['active_loan_count'] as int,
      paidLoanCount: json['paid_loan_count'] as int,
    );
  }
}

class CollectionsSummaryModel {
  final String fromDate;
  final String toDate;
  final String totalPaymentAmount;
  final String principalAllocation;
  final String interestAllocation;
  final String unappliedCreditAllocation;

  const CollectionsSummaryModel({
    required this.fromDate,
    required this.toDate,
    required this.totalPaymentAmount,
    required this.principalAllocation,
    required this.interestAllocation,
    required this.unappliedCreditAllocation,
  });

  factory CollectionsSummaryModel.fromJson(Map<String, dynamic> json) {
    return CollectionsSummaryModel(
      fromDate: json['from_date'] as String,
      toDate: json['to_date'] as String,
      totalPaymentAmount: json['total_payment_amount'].toString(),
      principalAllocation: json['principal_allocation'].toString(),
      interestAllocation: json['interest_allocation'].toString(),
      unappliedCreditAllocation: json['unapplied_credit_allocation'].toString(),
    );
  }
}

class AccountBalanceModel {
  final String code;
  final String name;
  final String normalBalance;
  final String balance;

  const AccountBalanceModel({
    required this.code,
    required this.name,
    required this.normalBalance,
    required this.balance,
  });

  factory AccountBalanceModel.fromJson(Map<String, dynamic> json) {
    return AccountBalanceModel(
      code: json['code'] as String,
      name: json['name'] as String,
      normalBalance: json['normal_balance'] as String,
      balance: json['balance'].toString(),
    );
  }
}

class OwnerDashboardModel {
  final PortfolioSnapshotModel portfolio;
  final CollectionsSummaryModel collections;
  final List<AccountBalanceModel> accountingBalances;
  final List<StatusCountModel> loanRequestStatusCounts;

  const OwnerDashboardModel({
    required this.portfolio,
    required this.collections,
    required this.accountingBalances,
    required this.loanRequestStatusCounts,
  });

  factory OwnerDashboardModel.fromJson(Map<String, dynamic> json) {
    final loanRequests = json['loan_requests'] as Map<String, dynamic>;
    return OwnerDashboardModel(
      portfolio: PortfolioSnapshotModel.fromJson(
          json['portfolio'] as Map<String, dynamic>),
      collections: CollectionsSummaryModel.fromJson(
          json['collections'] as Map<String, dynamic>),
      accountingBalances: (json['accounting_balances'] as List<dynamic>)
          .map((item) =>
              AccountBalanceModel.fromJson(item as Map<String, dynamic>))
          .toList(),
      loanRequestStatusCounts: (loanRequests['status_counts'] as List<dynamic>)
          .map(
              (item) => StatusCountModel.fromJson(item as Map<String, dynamic>))
          .toList(),
    );
  }

  bool get isEmpty =>
      portfolio.statusCounts.every((item) => item.count == 0) &&
      loanRequestStatusCounts.every((item) => item.count == 0) &&
      collections.totalPaymentAmount == '0.00';
}

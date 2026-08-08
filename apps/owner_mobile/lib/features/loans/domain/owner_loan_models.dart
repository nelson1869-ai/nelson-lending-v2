import 'package:flutter/foundation.dart';

@immutable
class BorrowerSummaryModel {
  final String id;
  final String firstName;
  final String lastName;
  final String phoneNumberNormalized;

  const BorrowerSummaryModel({
    required this.id,
    required this.firstName,
    required this.lastName,
    required this.phoneNumberNormalized,
  });

  String get fullName => '$firstName $lastName';

  factory BorrowerSummaryModel.fromJson(Map<String, dynamic> json) {
    return BorrowerSummaryModel(
      id: json['id'] as String,
      firstName: json['firstName'] as String,
      lastName: json['lastName'] as String,
      phoneNumberNormalized: json['phoneNumberNormalized'] as String,
    );
  }
}

@immutable
class ScheduleItemModel {
  final int installmentNumber;
  final String dueDate;
  final String openingPrincipal;
  final String interestDue;
  final String scheduledPrincipal;
  final String scheduledPayment;
  final String closingPrincipal;

  const ScheduleItemModel({
    required this.installmentNumber,
    required this.dueDate,
    required this.openingPrincipal,
    required this.interestDue,
    required this.scheduledPrincipal,
    required this.scheduledPayment,
    required this.closingPrincipal,
  });

  factory ScheduleItemModel.fromJson(Map<String, dynamic> json) {
    return ScheduleItemModel(
      installmentNumber: json['installmentNumber'] as int,
      dueDate: json['dueDate'] as String,
      openingPrincipal: json['openingPrincipal'] as String,
      interestDue: json['interestDue'] as String,
      scheduledPrincipal: json['scheduledPrincipal'] as String,
      scheduledPayment: json['scheduledPayment'] as String,
      closingPrincipal: json['closingPrincipal'] as String,
    );
  }
}

@immutable
class LoanQuoteModel {
  final String principal;
  final String monthlyRate;
  final int termMonths;
  final String paymentFrequency;
  final int numberOfPayments;
  final String periodRate;
  final String scheduledPayment;
  final String totalScheduledInterest;
  final String totalScheduledRepayment;
  final String firstDueDate;
  final String finalDueDate;
  final List<ScheduleItemModel> schedule;

  const LoanQuoteModel({
    required this.principal,
    required this.monthlyRate,
    required this.termMonths,
    required this.paymentFrequency,
    required this.numberOfPayments,
    required this.periodRate,
    required this.scheduledPayment,
    required this.totalScheduledInterest,
    required this.totalScheduledRepayment,
    required this.firstDueDate,
    required this.finalDueDate,
    required this.schedule,
  });

  factory LoanQuoteModel.fromJson(Map<String, dynamic> json) {
    final rawList = json['schedule'] as List<dynamic>? ?? [];
    return LoanQuoteModel(
      principal: json['principal'] as String,
      monthlyRate: json['monthlyRate'] as String,
      termMonths: json['termMonths'] as int,
      paymentFrequency: json['paymentFrequency'] as String,
      numberOfPayments: json['numberOfPayments'] as int,
      periodRate: json['periodRate'] as String,
      scheduledPayment: json['scheduledPayment'] as String,
      totalScheduledInterest: json['totalScheduledInterest'] as String,
      totalScheduledRepayment: json['totalScheduledRepayment'] as String,
      firstDueDate: json['firstDueDate'] as String,
      finalDueDate: json['finalDueDate'] as String,
      schedule: rawList
          .map((e) => ScheduleItemModel.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

@immutable
class OwnerLoanModel {
  final String id;
  final String? loanRequestId;
  final String borrowerId;
  final BorrowerSummaryModel? borrower;
  final String originalPrincipal;
  final String outstandingPrincipal;
  final String monthlyRate;
  final int termMonths;
  final String paymentFrequency;
  final int numberOfPayments;
  final String firstDueDate;
  final String finalDueDate;
  final String status;
  final String? disbursedAt;
  final String? cancelledAt;
  final String? paidAt;
  final String? defaultedAt;
  final String createdAt;
  final String updatedAt;

  const OwnerLoanModel({
    required this.id,
    this.loanRequestId,
    required this.borrowerId,
    this.borrower,
    required this.originalPrincipal,
    required this.outstandingPrincipal,
    required this.monthlyRate,
    required this.termMonths,
    required this.paymentFrequency,
    required this.numberOfPayments,
    required this.firstDueDate,
    required this.finalDueDate,
    required this.status,
    this.disbursedAt,
    this.cancelledAt,
    this.paidAt,
    this.defaultedAt,
    required this.createdAt,
    required this.updatedAt,
  });

  factory OwnerLoanModel.fromJson(Map<String, dynamic> json) {
    return OwnerLoanModel(
      id: json['id'] as String,
      loanRequestId: json['loanRequestId'] as String?,
      borrowerId: json['borrowerId'] as String,
      borrower: json['borrower'] != null
          ? BorrowerSummaryModel.fromJson(
              json['borrower'] as Map<String, dynamic>)
          : null,
      originalPrincipal: json['originalPrincipal'] as String,
      outstandingPrincipal: json['outstandingPrincipal'] as String,
      monthlyRate: json['monthlyRate'] as String,
      termMonths: json['termMonths'] as int,
      paymentFrequency: json['paymentFrequency'] as String,
      numberOfPayments: json['numberOfPayments'] as int,
      firstDueDate: json['firstDueDate'] as String,
      finalDueDate: json['finalDueDate'] as String,
      status: json['status'] as String,
      disbursedAt: json['disbursedAt'] as String?,
      cancelledAt: json['cancelledAt'] as String?,
      paidAt: json['paidAt'] as String?,
      defaultedAt: json['defaultedAt'] as String?,
      createdAt: json['createdAt'] as String,
      updatedAt: json['updatedAt'] as String,
    );
  }
}

@immutable
class OwnerLoanDetailModel extends OwnerLoanModel {
  final LoanQuoteModel quotePreview;

  const OwnerLoanDetailModel({
    required super.id,
    super.loanRequestId,
    required super.borrowerId,
    super.borrower,
    required super.originalPrincipal,
    required super.outstandingPrincipal,
    required super.monthlyRate,
    required super.termMonths,
    required super.paymentFrequency,
    required super.numberOfPayments,
    required super.firstDueDate,
    required super.finalDueDate,
    required super.status,
    super.disbursedAt,
    super.cancelledAt,
    super.paidAt,
    super.defaultedAt,
    required super.createdAt,
    required super.updatedAt,
    required this.quotePreview,
  });

  factory OwnerLoanDetailModel.fromJson(Map<String, dynamic> json) {
    final parent = OwnerLoanModel.fromJson(json);
    return OwnerLoanDetailModel(
      id: parent.id,
      loanRequestId: parent.loanRequestId,
      borrowerId: parent.borrowerId,
      borrower: parent.borrower,
      originalPrincipal: parent.originalPrincipal,
      outstandingPrincipal: parent.outstandingPrincipal,
      monthlyRate: parent.monthlyRate,
      termMonths: parent.termMonths,
      paymentFrequency: parent.paymentFrequency,
      numberOfPayments: parent.numberOfPayments,
      firstDueDate: parent.firstDueDate,
      finalDueDate: parent.finalDueDate,
      status: parent.status,
      disbursedAt: parent.disbursedAt,
      cancelledAt: parent.cancelledAt,
      paidAt: parent.paidAt,
      defaultedAt: parent.defaultedAt,
      createdAt: parent.createdAt,
      updatedAt: parent.updatedAt,
      quotePreview:
          LoanQuoteModel.fromJson(json['quotePreview'] as Map<String, dynamic>),
    );
  }
}

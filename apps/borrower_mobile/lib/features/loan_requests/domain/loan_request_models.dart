class ScheduleItemModel {
  final int paymentNumber;
  final String dueDate;
  final double paymentAmount;
  final double interestPaid;
  final double principalPaid;
  final double remainingPrincipal;

  const ScheduleItemModel({
    required this.paymentNumber,
    required this.dueDate,
    required this.paymentAmount,
    required this.interestPaid,
    required this.principalPaid,
    required this.remainingPrincipal,
  });

  factory ScheduleItemModel.fromJson(Map<String, dynamic> json) {
    return ScheduleItemModel(
      paymentNumber:
          (json['paymentNumber'] ?? json['installmentNumber'] as num).toInt(),
      dueDate: json['dueDate'] as String,
      paymentAmount: num.parse(
              (json['paymentAmount'] ?? json['scheduledPayment']).toString())
          .toDouble(),
      interestPaid: num.parse(
              (json['interestPaid'] ?? json['interestDue']).toString())
          .toDouble(),
      principalPaid: num.parse(
              (json['principalPaid'] ?? json['scheduledPrincipal']).toString())
          .toDouble(),
      remainingPrincipal:
          num.parse((json['remainingPrincipal'] ?? json['closingPrincipal'])
                  .toString())
              .toDouble(),
    );
  }
}

class LoanQuoteModel {
  final double principal;
  final double monthlyRate;
  final int termMonths;
  final String paymentFrequency;
  final String firstDueDate;
  final int numberOfPayments;
  final double periodicPayment;
  final double totalInterest;
  final double totalAmount;
  final List<ScheduleItemModel> schedule;

  const LoanQuoteModel({
    required this.principal,
    required this.monthlyRate,
    required this.termMonths,
    required this.paymentFrequency,
    required this.firstDueDate,
    required this.numberOfPayments,
    required this.periodicPayment,
    required this.totalInterest,
    required this.totalAmount,
    required this.schedule,
  });

  factory LoanQuoteModel.fromJson(Map<String, dynamic> json) {
    final rawSchedule = json['schedule'] as List<dynamic>? ?? [];
    return LoanQuoteModel(
      principal: (num.parse(json['principal'].toString())).toDouble(),
      monthlyRate: (num.parse(json['monthlyRate'].toString())).toDouble(),
      termMonths: (json['termMonths'] as num).toInt(),
      paymentFrequency: json['paymentFrequency'] as String,
      firstDueDate: json['firstDueDate'] as String,
      numberOfPayments: (json['numberOfPayments'] as num).toInt(),
      periodicPayment: num.parse(
              (json['periodicPayment'] ?? json['scheduledPayment']).toString())
          .toDouble(),
      totalInterest: num.parse(
              (json['totalInterest'] ?? json['totalScheduledInterest'])
                  .toString())
          .toDouble(),
      totalAmount: num.parse(
              (json['totalAmount'] ?? json['totalScheduledRepayment']).toString())
          .toDouble(),
      schedule: rawSchedule
          .map((e) => ScheduleItemModel.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

class LoanRequestModel {
  final String id;
  final String borrowerId;
  final double requestedPrincipal;
  final double requestedMonthlyRate;
  final int requestedTermMonths;
  final String requestedPaymentFrequency;
  final String requestedFirstDueDate;
  final String status;
  final String submittedAt;
  final String createdAt;
  final String updatedAt;
  final LoanQuoteModel? quotePreview;

  const LoanRequestModel({
    required this.id,
    required this.borrowerId,
    required this.requestedPrincipal,
    required this.requestedMonthlyRate,
    required this.requestedTermMonths,
    required this.requestedPaymentFrequency,
    required this.requestedFirstDueDate,
    required this.status,
    required this.submittedAt,
    required this.createdAt,
    required this.updatedAt,
    this.quotePreview,
  });

  factory LoanRequestModel.fromJson(Map<String, dynamic> json) {
    return LoanRequestModel(
      id: json['id'] as String,
      borrowerId: json['borrowerId'] as String,
      requestedPrincipal:
          (num.parse(json['requestedPrincipal'].toString())).toDouble(),
      requestedMonthlyRate:
          (num.parse(json['requestedMonthlyRate'].toString())).toDouble(),
      requestedTermMonths: (json['requestedTermMonths'] as num).toInt(),
      requestedPaymentFrequency: json['requestedPaymentFrequency'] as String,
      requestedFirstDueDate: json['requestedFirstDueDate'] as String,
      status: json['status'] as String,
      submittedAt: json['submittedAt'] as String,
      createdAt: json['createdAt'] as String,
      updatedAt: json['updatedAt'] as String,
      quotePreview: json['quotePreview'] == null
          ? null
          : LoanQuoteModel.fromJson(
              json['quotePreview'] as Map<String, dynamic>),
    );
  }
}

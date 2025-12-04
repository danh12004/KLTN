import { Leaf, AlertTriangle, ShieldCheck, ClipboardList, Lightbulb } from 'lucide-react';

const ResultDisplay = ({ data }) => {
  if (!data) return null;

  if (data.error) {
    return (
      <div className="w-full p-6 bg-red-50 border border-red-200 rounded-2xl text-center">
        <AlertTriangle className="mx-auto h-12 w-12 text-red-500" />
        <h3 className="mt-4 text-xl font-semibold text-red-800">Đã xảy ra lỗi</h3>
        <p className="mt-1 text-red-700">{data.error}</p>
      </div>
    );
  }

  // Sửa đổi nhỏ để hiển thị plan.main_message nếu có
  if (data.plan?.main_message && !data.analysis) {
    return (
      <div className="w-full p-6 bg-emerald-50 border border-emerald-200 rounded-2xl text-center">
        <Leaf className="mx-auto h-12 w-12 text-emerald-500" />
        <h3 className="mt-4 text-xl font-semibold text-emerald-800">Phân Tích Hoàn Tất</h3>
        <p className="mt-1 text-emerald-700">{data.plan.main_message}</p>
      </div>
    );
  }

  const { analysis, treatment_plan, prognosis } = data;

  return (
    <div className="bg-white p-6 md:p-8 rounded-2xl shadow-lg w-full border border-slate-200 space-y-6">
      <h2 className="text-3xl font-bold text-center text-slate-800">Kết Quả & Kế Hoạch Hành Động</h2>
      <div className="space-y-5">
        {analysis && (
          <div className="border-l-4 border-blue-500 pl-4 py-2">
            <h3 className="font-semibold text-lg text-slate-700 mb-2 flex items-center gap-2"><ShieldCheck size={20} className="text-blue-500"/>Đánh Giá Rủi Ro</h3>
            <p className="text-sm text-slate-600"><strong>Nguy cơ:</strong> {analysis.risk_assessment}</p>
            <p className="text-sm text-slate-600"><strong>Thời tiết:</strong> {analysis.weather_summary}</p>
          </div>
        )}
        {treatment_plan && (
          <div className="border-l-4 border-emerald-500 pl-4 py-2 space-y-4">
            <h3 className="font-semibold text-lg text-slate-700 flex items-center gap-2"><ClipboardList size={20} className="text-emerald-500"/>Kế Hoạch Chi Tiết</h3>
            <p className="text-sm text-slate-800 bg-slate-100 p-3 rounded-md">{treatment_plan.main_message}</p>
            <div className="space-y-3 text-sm">
                {treatment_plan.optimal_spray_day?.date && (
                    <div>
                    <strong className="text-slate-600">🗓️ Thời điểm phun thuốc tốt nhất:</strong>
                    <p className="text-slate-800">{treatment_plan.optimal_spray_day.session} ngày {treatment_plan.optimal_spray_day.date}</p>
                    <em className="text-xs text-slate-500">(Lý do: {treatment_plan.optimal_spray_day.reason})</em>
                    </div>
                )}
                {treatment_plan.drug_info?.sản_phẩm_tham_khảo && (
                    <div>
                    <strong className="text-slate-600">💊 Thuốc đề xuất:</strong>
                    <p className="font-medium text-slate-800">{treatment_plan.drug_info.sản_phẩm_tham_khảo} ({treatment_plan.drug_info.hoạt_chất})</p>
                    <ul className="list-disc list-inside text-xs text-slate-600 mt-1 pl-1">
                        <li><strong>Liều lượng:</strong> {treatment_plan.drug_info.liều_lượng}</li>
                        <li><strong>Cách dùng:</strong> {treatment_plan.drug_info.cách_dùng}</li>
                    </ul>
                    </div>
                )}
                {treatment_plan.additional_actions?.length > 0 && (
                    <div>
                    <strong className="text-slate-600">📌 Biện pháp hỗ trợ:</strong>
                    <ul className="list-disc list-inside text-xs text-slate-600 mt-1 space-y-1 pl-1">
                        {treatment_plan.additional_actions.map((action, index) => <li key={index}>{action}</li>)}
                    </ul>
                    </div>
                )}
            </div>
          </div>
        )}
        {prognosis && (
          <div className="border-l-4 border-amber-500 pl-4 py-2">
            <h3 className="font-semibold text-lg text-slate-700 mb-2 flex items-center gap-2"><Lightbulb size={20} className="text-amber-500"/>Dự Báo</h3>
            <p className="text-sm text-slate-600">{prognosis}</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default ResultDisplay;
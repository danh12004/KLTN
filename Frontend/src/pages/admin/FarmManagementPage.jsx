import React, { useState, useEffect, useCallback } from "react";
import api from "../../api";
import Spinner from "../../components/Spinner";
import { Edit, Trash2, Eye, Plus, X } from "lucide-react";
import toast from "react-hot-toast";

const FarmManagementPage = () => {
  const [farms, setFarms] = useState([]);
  const [loading, setLoading] = useState(true);

  const [showForm, setShowForm] = useState(false);
  const [editFarm, setEditFarm] = useState(null);
  const [farmData, setFarmData] = useState({
    name: "",
    province: "",
    area_ha: "",
    rice_variety: "",
    owner_id: "",
  });

  const [confirmDelete, setConfirmDelete] = useState(null);
  const [viewFarm, setViewFarm] = useState(null);

  const fetchFarms = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get("/admin/farms");
      setFarms(response.data);
    } catch (error) {
      console.error("Lỗi khi lấy danh sách nông trại:", error);
      toast.error("Không tải được danh sách nông trại");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchFarms();
  }, [fetchFarms]);

  const handleSaveFarm = async () => {
    try {
      if (editFarm) {
        await api.put(`/admin/farms/${editFarm.id}`, farmData);
        setFarms((prev) =>
          prev.map((f) => (f.id === editFarm.id ? { ...f, ...farmData } : f))
        );
        toast.success("Cập nhật nông trại thành công!");
      } else {
        const response = await api.post("/admin/farms", farmData);
        setFarms((prev) => [...prev, response.data]);
        toast.success("Thêm nông trại thành công!");
      }
      setShowForm(false);
      setEditFarm(null);
      setFarmData({
        name: "",
        province: "",
        area_ha: "",
        rice_variety: "",
        owner_id: "",
      });
    } catch (error) {
      console.error(error);
      toast.error(editFarm ? "Cập nhật thất bại!" : "Thêm thất bại!");
    }
  };

  const handleDeleteFarm = async (farmId) => {
    try {
      await api.delete(`/admin/farms/${farmId}`);
      setFarms((prev) => prev.filter((f) => f.id !== farmId));
      setConfirmDelete(null);
      toast.success("Xóa nông trại thành công!");
    } catch (error) {
      console.error("Lỗi khi xóa nông trại:", error);
      toast.error("Xóa nông trại thất bại!");
    }
  };

  const openEditForm = (farm) => {
    setEditFarm(farm);
    setFarmData({
      name: farm.name,
      province: farm.province,
      area_ha: farm.area_ha,
      rice_variety: farm.rice_variety,
      owner_id: farm.owner?.id || "",
    });
    setShowForm(true);
  };

  if (loading) return <Spinner />;

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-slate-800">Quản lý Nông trại</h1>
        <button
          onClick={() => {
            setEditFarm(null);
            setFarmData({
              name: "",
              province: "",
              area_ha: "",
              rice_variety: "",
              owner_id: "",
            });
            setShowForm(true);
          }}
          className="flex items-center gap-2 bg-blue-600 text-white font-semibold py-2 px-4 rounded-lg hover:bg-blue-700 cursor-pointer shadow"
        >
          <Plus size={18} /> Thêm Nông trại
        </button>
      </div>

      {/* Bảng */}
      <div className="bg-white rounded-lg shadow-md border border-slate-200 overflow-hidden">
        <table className="w-full text-left">
          <thead className="bg-slate-50 border-b border-slate-200 text-sm text-slate-600">
            <tr>
              <th className="p-4">ID</th>
              <th className="p-4">Tên Nông trại</th>
              <th className="p-4">Chủ sở hữu</th>
              <th className="p-4">Tỉnh/Thành</th>
              <th className="p-4">Diện tích (ha)</th>
              <th className="p-4">Giống lúa</th>
              <th className="p-4">Hành động</th>
            </tr>
          </thead>
          <tbody>
            {farms.map((farm) => (
              <tr
                key={farm.id}
                className="border-b border-slate-200 hover:bg-slate-50"
              >
                <td className="p-4">{farm.id}</td>
                <td className="p-4 font-medium text-slate-800">{farm.name}</td>
                <td className="p-4">{farm.owner?.username || "N/A"}</td>
                <td className="p-4">{farm.province}</td>
                <td className="p-4">{farm.area_ha}</td>
                <td className="p-4">{farm.rice_variety}</td>
                <td className="p-4 flex gap-2">
                  <button
                    onClick={() => setViewFarm(farm)}
                    className="text-gray-600 hover:text-gray-800 cursor-pointer"
                    title="Xem chi tiết"
                  >
                    <Eye size={18} />
                  </button>
                  <button
                    onClick={() => openEditForm(farm)}
                    className="text-blue-600 hover:text-blue-800 cursor-pointer"
                    title="Chỉnh sửa"
                  >
                    <Edit size={18} />
                  </button>
                  <button
                    onClick={() => setConfirmDelete(farm)}
                    className="text-red-600 hover:text-red-800 cursor-pointer"
                    title="Xóa"
                  >
                    <Trash2 size={18} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Modal thêm/sửa */}
      {showForm && (
        <div className="fixed inset-0 bg-gray-900/40 backdrop-blur-sm flex justify-center items-center z-50">
          <div className="bg-white p-6 rounded-2xl shadow-2xl w-96 relative animate-fadeIn">
            <button
              onClick={() => setShowForm(false)}
              className="absolute top-3 right-3 text-slate-500 hover:text-slate-800 cursor-pointer"
            >
              <X size={20} />
            </button>
            <h2 className="text-lg font-bold mb-4">
              {editFarm ? "Chỉnh sửa Nông trại" : "Thêm Nông trại"}
            </h2>
            <div className="space-y-3">
              <input
                type="text"
                placeholder="Tên Nông trại"
                value={farmData.name}
                onChange={(e) =>
                  setFarmData({ ...farmData, name: e.target.value })
                }
                className="w-full border rounded-lg p-2"
              />
              <input
                type="text"
                placeholder="Tỉnh/Thành"
                value={farmData.province}
                onChange={(e) =>
                  setFarmData({ ...farmData, province: e.target.value })
                }
                className="w-full border rounded-lg p-2"
              />
              <input
                type="number"
                placeholder="Diện tích (ha)"
                value={farmData.area_ha}
                onChange={(e) =>
                  setFarmData({ ...farmData, area_ha: e.target.value })
                }
                className="w-full border rounded-lg p-2"
              />
              <input
                type="text"
                placeholder="Giống lúa"
                value={farmData.rice_variety}
                onChange={(e) =>
                  setFarmData({ ...farmData, rice_variety: e.target.value })
                }
                className="w-full border rounded-lg p-2"
              />
              <input
                type="text"
                placeholder="ID chủ sở hữu"
                value={farmData.owner_id}
                onChange={(e) =>
                  setFarmData({ ...farmData, owner_id: e.target.value })
                }
                className="w-full border rounded-lg p-2"
              />
            </div>
            <button
              onClick={handleSaveFarm}
              className="mt-4 w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 cursor-pointer"
            >
              {editFarm ? "Cập nhật" : "Thêm"}
            </button>
          </div>
        </div>
      )}

      {/* Modal xem chi tiết */}
      {viewFarm && (
        <div className="fixed inset-0 bg-gray-900/40 backdrop-blur-sm flex justify-center items-center z-50">
          <div className="bg-white p-6 rounded-2xl w-[400px] shadow-2xl relative animate-fadeIn">
            <button
              onClick={() => setViewFarm(null)}
              className="absolute top-3 right-3 text-slate-500 hover:text-slate-800 cursor-pointer"
            >
              <X size={20} />
            </button>
            <h2 className="text-lg font-bold mb-4">Chi tiết Nông trại</h2>
            <div className="space-y-2 text-slate-700">
              <p><strong>ID:</strong> {viewFarm.id}</p>
              <p><strong>Tên:</strong> {viewFarm.name}</p>
              <p><strong>Chủ sở hữu:</strong> {viewFarm.owner?.username || "N/A"}</p>
              <p><strong>Tỉnh/Thành:</strong> {viewFarm.province}</p>
              <p><strong>Diện tích:</strong> {viewFarm.area_ha} ha</p>
              <p><strong>Giống lúa:</strong> {viewFarm.rice_variety}</p>
            </div>
          </div>
        </div>
      )}

      {/* Modal xác nhận xóa */}
      {confirmDelete && (
        <div className="fixed inset-0 bg-gray-900/40 backdrop-blur-sm flex justify-center items-center z-50">
          <div className="bg-white p-6 rounded-2xl w-80 shadow-lg animate-fadeIn">
            <h2 className="text-lg font-bold mb-4 text-red-600">Xác nhận xóa</h2>
            <p className="text-slate-700">
              Bạn có chắc chắn muốn xóa nông trại{" "}
              <strong>{confirmDelete.name}</strong>?
            </p>
            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setConfirmDelete(null)}
                className="px-4 py-2 rounded-lg bg-slate-200 hover:bg-slate-300 cursor-pointer"
              >
                Hủy
              </button>
              <button
                onClick={() => handleDeleteFarm(confirmDelete.id)}
                className="px-4 py-2 rounded-lg bg-red-600 text-white hover:bg-red-700 cursor-pointer"
              >
                Xóa
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default FarmManagementPage;
